using crm.Models;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace crm.Data;

public class CrmDbContext(DbContextOptions<CrmDbContext> options) : IdentityDbContext<AppUser>(options)
{
    public DbSet<Company> Companies => Set<Company>();
    public DbSet<AppFile> AppFiles => Set<AppFile>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Company>(entity =>
        {
            entity.ToTable("companies");
            entity.HasKey(c => c.Id);
            entity.Property(c => c.Name).HasMaxLength(128).IsRequired();
            entity.HasIndex(c => c.Name).IsUnique();
        });

        modelBuilder.Entity<AppUser>(entity =>
        {
            entity.ToTable("app_users");
            entity.Property(u => u.DisplayName).HasMaxLength(256);
            entity.HasOne(u => u.Company)
                .WithMany(c => c.Users)
                .HasForeignKey(u => u.CompanyId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<AppFile>(entity =>
        {
            entity.ToTable("app_files");
            entity.HasKey(f => f.Id);
            entity.Property(f => f.FileName).HasMaxLength(256).IsRequired();
            entity.Property(f => f.Content).IsRequired();
            entity.HasIndex(f => f.CompanyId);
            entity.HasOne(f => f.Company)
                .WithMany(c => c.Files)
                .HasForeignKey(f => f.CompanyId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}
