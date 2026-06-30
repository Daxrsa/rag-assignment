using crm.Contracts.Companies;
using crm.Services;
using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[ApiController]
[Route("companies")]
public sealed class CompaniesController(ICompanyService companyService) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> Fetch()
    {
        var companies = await companyService.GetAllAsync();
        return Ok(companies);
    }

    [HttpPost]
    public async Task<IActionResult> Add([FromBody] CreateCompanyRequest request)
    {
        var result = await companyService.CreateAsync(request);
        if (!result.Success)
        {
            return ToActionResult(result);
        }

        return Created($"/companies/{result.Value!.Id}", result.Value);
    }

    [HttpPut("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateCompanyRequest request)
    {
        var result = await companyService.UpdateAsync(id, request);
        return ToActionResult(result);
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        var result = await companyService.DeleteAsync(id);
        if (result.Success)
        {
            return NoContent();
        }

        return ToActionResult(result);
    }

    private IActionResult ToActionResult<T>(ServiceResult<T> result)
    {
        if (result.Success)
        {
            return Ok(result.Value);
        }

        var payload = new { error = result.Message };
        return result.Error switch
        {
            ServiceError.BadRequest => BadRequest(payload),
            ServiceError.Conflict => Conflict(payload),
            ServiceError.NotFound => NotFound(payload),
            ServiceError.Unauthorized => Unauthorized(payload),
            _ => StatusCode(StatusCodes.Status500InternalServerError, new { error = "Unexpected service error." }),
        };
    }
}
