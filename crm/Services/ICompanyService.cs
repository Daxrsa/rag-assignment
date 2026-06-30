using crm.Contracts.Companies;

namespace crm.Services;

public interface ICompanyService
{
    Task<IReadOnlyList<CompanyResponse>> GetAllAsync();
    Task<ServiceResult<CompanyResponse>> CreateAsync(CreateCompanyRequest request);
    Task<ServiceResult<CompanyResponse>> UpdateAsync(int id, UpdateCompanyRequest request);
    Task<ServiceResult<bool>> DeleteAsync(int id);
}
