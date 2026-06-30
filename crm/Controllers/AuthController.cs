using crm.Contracts.Auth;
using crm.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

namespace crm.Controllers;

[ApiController]
[Route("auth")]
public sealed class AuthController(IAuthService authService) : ControllerBase
{
    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        var result = await authService.RegisterAsync(request);
        if (!result.Success)
        {
            return ToActionResult(result);
        }

        return Created("/auth/getloggedinuser", result.Value);
    }

    [HttpPost("seed-user")]
    public async Task<IActionResult> SeedUser([FromBody] SeedUserRequest request)
    {
        var result = await authService.SeedUserAsync(request);
        if (!result.Success)
        {
            return ToActionResult(result);
        }

        return Created("/auth/getloggedinuser", result.Value);
    }

    [Authorize]
    [HttpDelete("users")]
    public async Task<IActionResult> DeleteAllUsers()
    {
        var result = await authService.DeleteAllUsersAsync();
        return ToActionResult(result);
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        var result = await authService.LoginAsync(request);
        if (!result.Success || result.Value is null)
        {
            return ToActionResult(result);
        }

        return SignIn(result.Value, IdentityConstants.BearerScheme);
    }

    [Authorize]
    [HttpGet("getloggedinuser")]
    public async Task<IActionResult> GetLoggedInUser()
    {
        var result = await authService.GetLoggedInUserAsync(User);
        return ToActionResult(result);
    }

    private IActionResult ToActionResult<T>(ServiceResult<T> result)
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
