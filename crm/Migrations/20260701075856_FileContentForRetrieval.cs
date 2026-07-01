using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace crm.Migrations
{
    /// <inheritdoc />
    public partial class FileContentForRetrieval : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Content",
                table: "app_files",
                type: "text",
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Content",
                table: "app_files");
        }
    }
}
