using crm.Contracts.Files;
using crm.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[ApiController]
[Authorize]
[Route("files")]
public sealed class FilesController(IFileService fileService, IConfiguration configuration) : BaseController
{
    [HttpGet]
    public async Task<IActionResult> Fetch([FromQuery] string? company)
    {
        var result = await fileService.FetchAsync(User, company);
        return ToActionResult(result);
    }

    [HttpPost]
    public async Task<IActionResult> Upload([FromBody] UploadFileRequest request)
    {
        var result = await fileService.UploadAsync(User, request);
        if (!result.Success)
        {
            return ToActionResult(result);
        }

        return Created($"/files/{result.Value!.Id}", result.Value);
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        var result = await fileService.DeleteAsync(User, id);
        if (result.Success)
        {
            return NoContent();
        }

        return ToActionResult(result);
    }

    [AllowAnonymous]
    [HttpGet("internal/retrieval-documents")]
    public async Task<IActionResult> FetchForRetrieval(
        [FromQuery] int companyId,
        [FromQuery] int[]? documentIds,
        [FromHeader(Name = "X-Internal-Api-Key")] string? internalApiKey)
    {
        var expectedApiKey = configuration["InternalApi:ApiKey"];
        if (string.IsNullOrWhiteSpace(expectedApiKey) || internalApiKey != expectedApiKey)
        {
            return Unauthorized(new { error = "Invalid internal API key." });
        }

        var result = await fileService.FetchForRetrievalAsync(companyId, documentIds);
        return ToActionResult(result);
    }
}
