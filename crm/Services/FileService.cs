using System.Security.Claims;
using crm.Contracts.Files;
using crm.Data;
using crm.Models;
using Microsoft.EntityFrameworkCore;

namespace crm.Services;

public sealed class FileService(CrmDbContext db) : IFileService
{
    public async Task<ServiceResult<IReadOnlyList<FileResponse>>> FetchAsync(ClaimsPrincipal principal, string? company)
    {
        var userId = GetUserId(principal);
        if (string.IsNullOrWhiteSpace(userId))
        {
            return ServiceResult<IReadOnlyList<FileResponse>>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        var user = await db.Users.AsNoTracking()
            .FirstOrDefaultAsync(u => u.Id == userId);
        if (user is null)
        {
            return ServiceResult<IReadOnlyList<FileResponse>>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        IQueryable<AppFile> query = db.AppFiles.AsNoTracking()
            .Include(f => f.Company)
            .Where(f => f.CompanyId == user.CompanyId)
            .OrderBy(f => f.Id);

        if (!string.IsNullOrWhiteSpace(company))
        {
            query = query.Where(f => f.Company.Name == company);
        }

        var files = await query
            .Select(f => new FileResponse(f.Id, f.FileName, f.Company.Name, f.CreatedAtUtc))
            .ToListAsync();

        return ServiceResult<IReadOnlyList<FileResponse>>.Ok(files);
    }

    public async Task<ServiceResult<FileResponse>> UploadAsync(ClaimsPrincipal principal, UploadFileRequest request)
    {
        var userId = GetUserId(principal);
        if (string.IsNullOrWhiteSpace(userId))
        {
            return ServiceResult<FileResponse>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        if (string.IsNullOrWhiteSpace(request.FileName))
        {
            return ServiceResult<FileResponse>.Fail(ServiceError.BadRequest, "FileName is required.");
        }

        var user = await db.Users
            .Include(u => u.Company)
            .FirstOrDefaultAsync(u => u.Id == userId);
        if (user is null)
        {
            return ServiceResult<FileResponse>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        var file = new AppFile
        {
            FileName = request.FileName.Trim(),
            CompanyId = user.CompanyId,
            CreatedAtUtc = DateTime.UtcNow,
        };

        db.AppFiles.Add(file);
        await db.SaveChangesAsync();

        return ServiceResult<FileResponse>.Ok(new FileResponse(file.Id, file.FileName, user.Company.Name, file.CreatedAtUtc));
    }

    public async Task<ServiceResult<bool>> DeleteAsync(ClaimsPrincipal principal, int id)
    {
        var userId = GetUserId(principal);
        if (string.IsNullOrWhiteSpace(userId))
        {
            return ServiceResult<bool>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        var user = await db.Users.AsNoTracking()
            .FirstOrDefaultAsync(u => u.Id == userId);
        if (user is null)
        {
            return ServiceResult<bool>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        var file = await db.AppFiles.FirstOrDefaultAsync(f => f.Id == id && f.CompanyId == user.CompanyId);
        if (file is null)
        {
            return ServiceResult<bool>.Fail(ServiceError.NotFound, "File not found.");
        }

        db.AppFiles.Remove(file);
        await db.SaveChangesAsync();
        return ServiceResult<bool>.Ok(true);
    }

    private static string? GetUserId(ClaimsPrincipal principal)
        => principal.FindFirstValue(ClaimTypes.NameIdentifier) ?? principal.FindFirstValue("sub");
}
