namespace crm.Models;

public class AppFile
{
    public int Id { get; set; }
    public string FileName { get; set; } = string.Empty;
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    public int CompanyId { get; set; }
    public Company Company { get; set; } = null!;
}
