using crm.Contracts.Files;
using crm.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[Authorize]
[Route("files")]
public sealed class FilesController(IFileService fileService) : BaseController
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
}
