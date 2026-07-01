using System.Security.Claims;
using crm.Contracts.Retrieval;

namespace crm.Services;

public interface IRetrievalProxyService
{
    Task<ServiceResult<RetrievalResponse>> QueryAsync(ClaimsPrincipal principal, RetrievalRequest request);
}