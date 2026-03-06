#!/usr/bin/env python3
"""
Generate a PDF resume from info.json.

Usage:
    python generate_resume.py                     # reads info.json, writes resume.pdf
    python generate_resume.py -i data.json        # custom input
    python generate_resume.py -o my_resume.pdf    # custom output
"""

import argparse
import json
import sys
from pathlib import Path

from weasyprint import HTML


# ── HTML template ────────────────────────────────────────────────────────────

def build_html(data: dict) -> str:
    """Return a complete HTML string for the resume."""
    name = data.get("name", "")
    title = data.get("title", "")
    location = data.get("location", "")
    phone = data.get("phone", "")
    email = data.get("email", "")
    linkedin = data.get("linkedin", "")
    github = data.get("github", "")
    summary = data.get("summary", "")

    # ── Contact row ──
    contact_items = []
    if location:
        contact_items.append(f"<span>{location}</span>")
    if phone:
        contact_items.append(f"<span>{phone}</span>")
    if email:
        contact_items.append(f'<span><a href="mailto:{email}">{email}</a></span>')
    if linkedin:
        display = linkedin.replace("https://www.", "").replace("https://", "")
        contact_items.append(f'<span><a href="{linkedin}">{display}</a></span>')
    if github:
        display = github.replace("https://", "")
        contact_items.append(f'<span><a href="{github}">{display}</a></span>')
    contact_html = "\n            ".join(contact_items)

    # ── Skills ──
    skills = data.get("skills", {})
    skill_rows = ""
    for label, values in skills.items():
        if values:
            label_escaped = label.replace("&", "&amp;")
            skill_rows += f"""
            <tr>
                <td class="label">{label_escaped}</td>
                <td class="value">{", ".join(values)}</td>
            </tr>"""

    # ── Experience ──
    experience_html = ""
    for job in data.get("experience", []):
        job_title = job.get("title", "")
        company = job.get("company", "")
        duration = job.get("duration", "")
        tech_stack = job.get("tech_stack", [])
        achievements = job.get("achievements", [])

        bullets = "\n".join(f"                <li>{a}</li>" for a in achievements)
        tech_line = (
            f'<div class="job-tech">Tech: {", ".join(tech_stack)}</div>'
            if tech_stack
            else ""
        )

        experience_html += f"""
        <div class="job">
            <div class="job-header">
                <span class="job-title">{job_title}</span>
                <span class="job-date">{duration}</span>
            </div>
            <div class="job-company">{company}</div>
            {tech_line}
            <ul>
{bullets}
            </ul>
        </div>
"""

    # ── Education ──
    edu = data.get("education", {})
    edu_degree = edu.get("degree", "")
    edu_institution = edu.get("institution", "")
    edu_duration = edu.get("duration", "")
    edu_gpa = edu.get("gpa", "")
    gpa_text = f" — GPA: {edu_gpa}" if edu_gpa else ""

    # ── Projects ──
    projects = data.get("projects", [])
    projects_html = ""
    if projects:
        project_items = ""
        for proj in projects:
            proj_name = proj.get("name", "")
            proj_url = proj.get("url", "")
            proj_desc = proj.get("description", "")
            display_url = proj_url.replace("https://", "")
            project_items += f"""
        <div class="project">
            <span class="project-name">{proj_name}</span> — <a href="{proj_url}">{display_url}</a>
            <p>{proj_desc}</p>
        </div>"""
        projects_html = f"""
    <section class="section">
        <h2 class="section-title">Projects</h2>
        {project_items}
    </section>
"""

    # ── Interests & Profiles ──
    interests = data.get("interests", [])
    profiles = data.get("profiles", {})
    additional_rows = ""
    if interests:
        additional_rows += f"""
            <tr>
                <td class="label">Interests</td>
                <td class="value">{", ".join(interests)}</td>
            </tr>"""
    if profiles:
        profile_links = " · ".join(
            f'<a href="{url}">{name}</a>' for name, url in profiles.items()
        )
        additional_rows += f"""
            <tr>
                <td class="label">Profiles</td>
                <td class="value">{profile_links}</td>
            </tr>"""
    interests_html = ""
    if additional_rows:
        interests_html = f"""
    <section class="section">
        <h2 class="section-title">Additional</h2>
        <table class="skills-table">
            {additional_rows}
        </table>
    </section>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --text: #1a1a1a;
            --text-secondary: #444;
            --accent: #1a56db;
            --border: #d1d5db;
            --bg: #ffffff;
            --section-gap: 20px;
        }}

        html {{ font-size: 12.5px; }}

        body {{
            font-family: 'Inter', 'Segoe UI', Arial, Helvetica, sans-serif;
            color: var(--text);
            background: var(--bg);
            line-height: 1.55;
            max-width: 850px;
            margin: 0 auto;
            padding: 0;
        }}

        a {{ color: var(--accent); text-decoration: none; }}

        /* ---- Header ---- */
        .resume-header {{ text-align: center; margin-bottom: var(--section-gap); }}

        .resume-header h1 {{
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: var(--text);
            margin-bottom: 4px;
        }}

        .resume-header .tagline {{
            font-size: 1.05rem;
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: 10px;
        }}

        .contact-row {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 6px 20px;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}

        /* ---- Section ---- */
        .section {{ margin-bottom: var(--section-gap); }}

        .section-title {{
            font-size: 0.95rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--accent);
            border-bottom: 2px solid var(--accent);
            padding-bottom: 4px;
            margin-bottom: 12px;
        }}

        /* ---- Summary ---- */
        .summary p {{
            color: var(--text-secondary);
            font-size: 0.92rem;
            line-height: 1.65;
        }}

        /* ---- Skills ---- */
        .skills-table {{
            width: 100%;
            font-size: 0.9rem;
        }}

        .skills-table td {{
            padding: 3px 0;
            vertical-align: top;
        }}

        .skills-table .label {{
            font-weight: 600;
            width: 160px;
            color: var(--text);
            white-space: nowrap;
            padding-right: 12px;
        }}

        .skills-table .value {{
            color: var(--text-secondary);
        }}

        /* ---- Experience ---- */
        .job {{ margin-bottom: 18px; }}
        .job:last-child {{ margin-bottom: 0; }}

        .job-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            flex-wrap: wrap;
            margin-bottom: 2px;
        }}

        .job-title {{
            font-size: 1rem;
            font-weight: 700;
            color: var(--text);
        }}

        .job-date {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
            white-space: nowrap;
        }}

        .job-company {{
            font-size: 0.92rem;
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: 6px;
        }}

        .job-tech {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 6px;
            font-style: italic;
        }}

        .job ul {{
            padding-left: 18px;
            margin: 0;
        }}

        .job li {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 3px;
            line-height: 1.55;
        }}

        .job li strong {{
            color: var(--text);
            font-weight: 600;
        }}

        /* ---- Education ---- */
        .edu-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}
        .edu-degree {{ font-weight: 600; font-size: 0.95rem; }}
        .edu-date {{ font-size: 0.85rem; color: var(--text-secondary); }}
        .edu-school {{ font-size: 0.9rem; color: var(--text-secondary); }}

        /* ---- Projects ---- */
        .project {{ margin-bottom: 10px; }}
        .project-name {{ font-weight: 600; font-size: 0.95rem; }}
        .project p {{ font-size: 0.9rem; color: var(--text-secondary); margin-top: 2px; }}

        @page {{
            margin: 0.55in 0.6in;
        }}
    </style>
</head>
<body>

    <!-- ============ HEADER ============ -->
    <header class="resume-header">
        <h1>{name}</h1>
        <p class="tagline">{title}</p>
        <div class="contact-row">
            {contact_html}
        </div>
    </header>

    <!-- ============ SUMMARY ============ -->
    <section class="section summary">
        <h2 class="section-title">Professional Summary</h2>
        <p>{summary}</p>
    </section>

    <!-- ============ SKILLS ============ -->
    <section class="section">
        <h2 class="section-title">Technical Skills</h2>
        <table class="skills-table">
            {skill_rows}
        </table>
    </section>

    <!-- ============ EXPERIENCE ============ -->
    <section class="section">
        <h2 class="section-title">Professional Experience</h2>
        {experience_html}
    </section>

    {projects_html}

    <!-- ============ EDUCATION ============ -->
    <section class="section">
        <h2 class="section-title">Education</h2>
        <div class="edu-header">
            <span class="edu-degree">{edu_degree}</span>
            <span class="edu-date">{edu_duration}</span>
        </div>
        <div class="edu-school">{edu_institution}{gpa_text}</div>
    </section>

    {interests_html}

</body>
</html>
"""


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a PDF resume from a JSON file.")
    parser.add_argument(
        "-i", "--input",
        default="info.json",
        help="Path to the JSON data file (default: info.json)",
    )
    parser.add_argument(
        "-o", "--output",
        default="resume.pdf",
        help="Output PDF file path (default: resume.pdf)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    html_content = build_html(data)

    HTML(string=html_content).write_pdf(args.output)
    print(f"✓ Resume saved to {args.output}")


if __name__ == "__main__":
    main()
