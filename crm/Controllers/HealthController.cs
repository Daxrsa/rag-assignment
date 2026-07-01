using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[Route("health")]
public sealed class HealthController : BaseController
{
    [HttpGet]
    public IActionResult Get() => Ok(new { status = "ok" });
}
