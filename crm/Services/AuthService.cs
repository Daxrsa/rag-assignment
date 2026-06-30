using System.Security.Claims;
using crm.Contracts.Auth;
using crm.Data;
using crm.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace crm.Services;

public sealed class AuthService(
    UserManager<AppUser> userManager,
    SignInManager<AppUser> signInManager,
    CrmDbContext db) : IAuthService
{
    public async Task<ServiceResult<UserResponse>> RegisterAsync(RegisterRequest request)
        => await CreateUserWithCompanyAsync(request.Email, request.Password, request.Company, request.DisplayName);

    public async Task<ServiceResult<UserResponse>> SeedUserAsync(SeedUserRequest request)
        => await CreateUserWithCompanyAsync(request.Email, request.Password, request.Company, request.DisplayName);

    private async Task<ServiceResult<UserResponse>> CreateUserWithCompanyAsync(
        string email,
        string password,
        string companyInput,
        string? displayName)
    {
        if (string.IsNullOrWhiteSpace(email) ||
            string.IsNullOrWhiteSpace(password) ||
            string.IsNullOrWhiteSpace(companyInput))
        {
            return ServiceResult<UserResponse>.Fail(ServiceError.BadRequest, "Email, password, and company are required.");
        }

        var normalizedEmail = email.Trim();
        var existingUser = await userManager.FindByEmailAsync(normalizedEmail);
        if (existingUser is not null)
        {
            return ServiceResult<UserResponse>.Fail(ServiceError.Conflict, "A user with this email already exists.");
        }

        var companyName = companyInput.Trim();
        var company = await db.Companies.FirstOrDefaultAsync(c => c.Name == companyName);
        if (company is null)
        {
            company = new Company { Name = companyName };
            db.Companies.Add(company);
            await db.SaveChangesAsync();
        }

        var user = new AppUser
        {
            UserName = normalizedEmail,
            Email = normalizedEmail,
            DisplayName = string.IsNullOrWhiteSpace(displayName)
                ? normalizedEmail
                : displayName.Trim(),
            CompanyId = company.Id,
        };

        var createResult = await userManager.CreateAsync(user, password);
        if (!createResult.Succeeded)
        {
            return ServiceResult<UserResponse>.Validation(createResult.Errors.Select(e => e.Description).ToArray());
        }

        return ServiceResult<UserResponse>.Ok(new UserResponse(user.Id, user.Email, user.DisplayName, company.Name));
    }

    public async Task<ServiceResult<ClaimsPrincipal>> LoginAsync(LoginRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
        {
            return ServiceResult<ClaimsPrincipal>.Fail(ServiceError.BadRequest, "Email and password are required.");
        }

        var user = await userManager.FindByEmailAsync(request.Email);
        if (user is null)
        {
            return ServiceResult<ClaimsPrincipal>.Fail(ServiceError.Unauthorized, "Invalid credentials.");
        }

        var passwordResult = await signInManager.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
        if (!passwordResult.Succeeded)
        {
            return ServiceResult<ClaimsPrincipal>.Fail(ServiceError.Unauthorized, "Invalid credentials.");
        }

        var principal = await signInManager.CreateUserPrincipalAsync(user);
        return ServiceResult<ClaimsPrincipal>.Ok(principal);
    }

    public async Task<ServiceResult<DeleteUsersResponse>> DeleteAllUsersAsync()
    {
        var users = await db.Users.ToListAsync();
        var deletedCount = 0;

        foreach (var user in users)
        {
            var deleteResult = await userManager.DeleteAsync(user);
            if (!deleteResult.Succeeded)
            {
                return ServiceResult<DeleteUsersResponse>.Validation(
                    deleteResult.Errors.Select(e => e.Description).ToArray());
            }

            deletedCount++;
        }

        return ServiceResult<DeleteUsersResponse>.Ok(new DeleteUsersResponse(deletedCount));
    }

    public async Task<ServiceResult<UserResponse>> GetLoggedInUserAsync(ClaimsPrincipal principal)
    {
        var userId = GetUserId(principal);
        if (string.IsNullOrWhiteSpace(userId))
        {
            return ServiceResult<UserResponse>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        var user = await db.Users.AsNoTracking()
            .Include(u => u.Company)
            .FirstOrDefaultAsync(u => u.Id == userId);

        if (user is null)
        {
            return ServiceResult<UserResponse>.Fail(ServiceError.Unauthorized, "Unauthorized.");
        }

        return ServiceResult<UserResponse>.Ok(new UserResponse(user.Id, user.Email, user.DisplayName, user.Company.Name));
    }

    private static string? GetUserId(ClaimsPrincipal principal)
        => principal.FindFirstValue(ClaimTypes.NameIdentifier) ?? principal.FindFirstValue("sub");
}
