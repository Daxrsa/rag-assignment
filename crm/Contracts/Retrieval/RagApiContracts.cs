namespace crm.Contracts.Retrieval;

internal sealed record RagApiChatRequest(
    string Message,
    string? SessionId,
    string UserId,
    string Company,
    int CompanyId,
    IReadOnlyList<int> AllowedDocumentIds,
    string TenantIndexName);

internal sealed record RagApiChatResponse(
    string? SessionId,
    string? Answer,
    double? TopScore,
    string? Error);