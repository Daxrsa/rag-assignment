using crm.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[Authorize]
[Route("access-policy")]
public sealed class AccessPolicyController(IAccessPolicyService accessPolicyService) : BaseController
{
    [HttpGet("retrieval")]
    public async Task<IActionResult> BuildRetrievalPolicy([FromQuery] int[]? documentIds)
    {
        var result = await accessPolicyService.BuildForRetrievalAsync(User, documentIds);
        return ToActionResult(result);
    }
}