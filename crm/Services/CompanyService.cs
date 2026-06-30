using crm.Contracts.Companies;
using crm.Data;
using crm.Models;
using Microsoft.EntityFrameworkCore;

namespace crm.Services;

public sealed class CompanyService(CrmDbContext db) : ICompanyService
{
    public async Task<IReadOnlyList<CompanyResponse>> GetAllAsync()
    {
        return await db.Companies.AsNoTracking()
            .OrderBy(c => c.Name)
            .Select(c => new CompanyResponse(c.Id, c.Name))
            .ToListAsync();
    }

    public async Task<ServiceResult<CompanyResponse>> CreateAsync(CreateCompanyRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Name))
        {
            return ServiceResult<CompanyResponse>.Fail(ServiceError.BadRequest, "Company name is required.");
        }

        var name = request.Name.Trim();
        var exists = await db.Companies.AnyAsync(c => c.Name == name);
        if (exists)
        {
            return ServiceResult<CompanyResponse>.Fail(ServiceError.Conflict, "A company with this name already exists.");
        }

        var company = new Company { Name = name };
        db.Companies.Add(company);
        await db.SaveChangesAsync();

        return ServiceResult<CompanyResponse>.Ok(new CompanyResponse(company.Id, company.Name));
    }

    public async Task<ServiceResult<CompanyResponse>> UpdateAsync(int id, UpdateCompanyRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Name))
        {
            return ServiceResult<CompanyResponse>.Fail(ServiceError.BadRequest, "Company name is required.");
        }

        var company = await db.Companies.FirstOrDefaultAsync(c => c.Id == id);
        if (company is null)
        {
            return ServiceResult<CompanyResponse>.Fail(ServiceError.NotFound, "Company not found.");
        }

        var name = request.Name.Trim();
        var duplicate = await db.Companies.AnyAsync(c => c.Name == name && c.Id != id);
        if (duplicate)
        {
            return ServiceResult<CompanyResponse>.Fail(ServiceError.Conflict, "A company with this name already exists.");
        }

        company.Name = name;
        await db.SaveChangesAsync();
        return ServiceResult<CompanyResponse>.Ok(new CompanyResponse(company.Id, company.Name));
    }

    public async Task<ServiceResult<bool>> DeleteAsync(int id)
    {
        var company = await db.Companies.FirstOrDefaultAsync(c => c.Id == id);
        if (company is null)
        {
            return ServiceResult<bool>.Fail(ServiceError.NotFound, "Company not found.");
        }

        db.Companies.Remove(company);
        await db.SaveChangesAsync();
        return ServiceResult<bool>.Ok(true);
    }
}
