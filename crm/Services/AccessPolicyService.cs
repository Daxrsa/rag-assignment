using System.Security.Claims;
using crm.Contracts.Auth;
using crm.Data;
using Microsoft.EntityFrameworkCore;

namespace crm.Services;

public sealed class AccessPolicyService(CrmDbContext db) : IAccessPolicyService
{
    public async Task<ServiceResult<AccessPolicyResponse>> BuildForRetrievalAsync(
        ClaimsPrincipal principal,
        IReadOnlyCollection<int>? requestedDocumentIds)
    {
        var userId = GetUserId(principal);
        if (string.IsNullOrWhiteSpace(userId))
        {
            return ServiceResult<AccessPolicyResponse>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        var user = await db.Users.AsNoTracking()
            .Include(u => u.Company)
            .FirstOrDefaultAsync(u => u.Id == userId);
        if (user is null)
        {
            return ServiceResult<AccessPolicyResponse>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        var requestedIds = (requestedDocumentIds ?? Array.Empty<int>())
            .Where(id => id > 0)
            .Distinct()
            .ToArray();

        var allowedQuery = db.AppFiles.AsNoTracking()
            .Where(f => f.CompanyId == user.CompanyId);

        if (requestedIds.Length > 0)
        {
            allowedQuery = allowedQuery.Where(f => requestedIds.Contains(f.Id));
        }

        var allowedDocuments = await allowedQuery
            .OrderBy(f => f.Id)
            .Select(f => new AllowedDocumentResponse(f.Id, f.FileName))
            .ToListAsync();

        if (requestedIds.Length > 0 && allowedDocuments.Count != requestedIds.Length)
        {
            return ServiceResult<AccessPolicyResponse>.Fail(
                ServiceError.Unauthorized,
                "One or more requested documents are outside your company scope.");
        }

        var roles = principal.Claims
            .Where(c => c.Type == ClaimTypes.Role || c.Type == "role")
            .Select(c => c.Value)
            .Where(v => !string.IsNullOrWhiteSpace(v))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToArray();

        if (roles.Length == 0)
        {
            roles = ["member"];
        }

        var policy = new AccessPolicyResponse(
            user.CompanyId,
            user.Company.Name,
            roles,
            allowedDocuments,
            $"company_{user.CompanyId}",
            new RetrievalMetadataFilter(user.CompanyId));

        return ServiceResult<AccessPolicyResponse>.Ok(policy);
    }

    private static string? GetUserId(ClaimsPrincipal principal)
        => principal.FindFirstValue(ClaimTypes.NameIdentifier) ?? principal.FindFirstValue("sub");
}