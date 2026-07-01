using System.Security.Claims;
using crm.Contracts.Auth;

namespace crm.Services;

public interface IAccessPolicyService
{
    Task<ServiceResult<AccessPolicyResponse>> BuildForRetrievalAsync(ClaimsPrincipal principal, IReadOnlyCollection<int>? requestedDocumentIds);
}