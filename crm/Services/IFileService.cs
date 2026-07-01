using System.Security.Claims;
using crm.Contracts.Files;

namespace crm.Services;

public interface IFileService
{
    Task<ServiceResult<IReadOnlyList<FileResponse>>> FetchAsync(ClaimsPrincipal principal, string? company);
    Task<ServiceResult<FileResponse>> UploadAsync(ClaimsPrincipal principal, UploadFileRequest request);
    Task<ServiceResult<IReadOnlyList<RetrievalDocumentResponse>>> FetchForRetrievalAsync(int companyId, IReadOnlyCollection<int>? documentIds);
    Task<ServiceResult<bool>> DeleteAsync(ClaimsPrincipal principal, int id);
}
