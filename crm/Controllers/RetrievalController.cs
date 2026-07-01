using crm.Contracts.Retrieval;
using crm.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[Authorize]
[Route("retrieval")]
public sealed class RetrievalController(IRetrievalProxyService retrievalProxyService) : BaseController
{
    [HttpPost("query")]
    public async Task<IActionResult> Query([FromBody] RetrievalRequest request)
    {
        var result = await retrievalProxyService.QueryAsync(User, request);
        return ToActionResult(result);
    }
}