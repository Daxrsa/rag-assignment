using crm.Services;
using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[ApiController]
public abstract class BaseController : ControllerBase
{
    protected IActionResult ToActionResult<T>(ServiceResult<T> result)
    {
        if (result.Success)
        {
            return Ok(result.Value);
        }

        object payload = new { error = result.Message };
        if (result.ValidationErrors is { Length: > 0 })
        {
            payload = new { error = result.Message, errors = result.ValidationErrors };
        }

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