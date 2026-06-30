using System.Security.Claims;
using crm.Contracts.Auth;

namespace crm.Services;

public interface IAuthService
{
    Task<ServiceResult<UserResponse>> RegisterAsync(RegisterRequest request);
    Task<ServiceResult<UserResponse>> SeedUserAsync(SeedUserRequest request);
    Task<ServiceResult<DeleteUsersResponse>> DeleteAllUsersAsync();
    Task<ServiceResult<ClaimsPrincipal>> LoginAsync(LoginRequest request);
    Task<ServiceResult<UserResponse>> GetLoggedInUserAsync(ClaimsPrincipal principal);
}
