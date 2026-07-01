using System.Security.Claims;
using System.Net.Http.Json;
using crm.Contracts.Retrieval;

namespace crm.Services;

public sealed class RetrievalProxyService(
    IAccessPolicyService accessPolicyService,
    IHttpClientFactory httpClientFactory,
    IConfiguration configuration) : IRetrievalProxyService
{
    public async Task<ServiceResult<RetrievalResponse>> QueryAsync(ClaimsPrincipal principal, RetrievalRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Message))
        {
            return ServiceResult<RetrievalResponse>.Fail(ServiceError.BadRequest, "Message is required.");
        }

        var requestedDocumentIds = request.DocumentIds?
            .Where(id => id > 0)
            .Distinct()
            .ToArray();

        var policyResult = await accessPolicyService.BuildForRetrievalAsync(principal, requestedDocumentIds);
        if (!policyResult.Success || policyResult.Value is null)
        {
            return ServiceResult<RetrievalResponse>.Fail(
                policyResult.Error,
                policyResult.Message ?? "Access policy denied.");
        }

        var policy = policyResult.Value;
        var ragApiBaseUrl = configuration["RagApi:BaseUrl"];
        if (string.IsNullOrWhiteSpace(ragApiBaseUrl))
        {
            return ServiceResult<RetrievalResponse>.Fail(
                ServiceError.BadRequest,
                "RAG API base URL is not configured. Set RagApi:BaseUrl.");
        }

        var client = httpClientFactory.CreateClient("RagApi");
        if (client.BaseAddress is null)
        {
            client.BaseAddress = new Uri(ragApiBaseUrl, UriKind.Absolute);
        }

        var payload = new RagApiChatRequest(
            request.Message.Trim(),
            request.SessionId,
            policy.Company,
            policy.CompanyId,
            policy.AllowedDocuments.Select(d => d.Id).ToArray(),
            policy.TenantIndexName);

        HttpResponseMessage httpResponse;
        try
        {
            httpResponse = await client.PostAsJsonAsync("/chat", payload);
        }
        catch
        {
            return ServiceResult<RetrievalResponse>.Fail(
                ServiceError.BadRequest,
                "Could not reach RAG API.");
        }

        RagApiChatResponse? ragResponse;
        try
        {
            ragResponse = await httpResponse.Content.ReadFromJsonAsync<RagApiChatResponse>();
        }
        catch
        {
            ragResponse = null;
        }

        if (!httpResponse.IsSuccessStatusCode)
        {
            var apiError = ragResponse?.Error;
            return ServiceResult<RetrievalResponse>.Fail(
                ServiceError.BadRequest,
                string.IsNullOrWhiteSpace(apiError) ? "RAG API request failed." : apiError);
        }

        if (ragResponse is null || string.IsNullOrWhiteSpace(ragResponse.Answer) || string.IsNullOrWhiteSpace(ragResponse.SessionId))
        {
            return ServiceResult<RetrievalResponse>.Fail(ServiceError.BadRequest, "Invalid response from RAG API.");
        }

        var response = new RetrievalResponse(
            ragResponse.SessionId,
            ragResponse.Answer,
            ragResponse.TopScore ?? 0,
            policy);

        return ServiceResult<RetrievalResponse>.Ok(response);
    }
}