class CaseOverview {
  academic_summary string @description("A concise summary of the student's academic performance and risks based on the provided metrics.")
  action_keys string[] @description("Exactly 3 concise action keys (short phrases) for the advisor to focus on.")
}

function GenerateCaseOverview(performance_data: string) -> CaseOverview {
  client Gemini_31_Flash_Lite
  prompt #"
    Generate an academic overview and 3 action keys for a student based on their performance data.

    STUDENT PERFORMANCE DATA:
    {{ performance_data }}

    INSTRUCTIONS:
    1. Analyze the student's term metrics, course averages, and trends.
    2. Write a professional, data-driven academic summary (2-3 sentences).
    3. Identify 3 critical action items for an academic advisor. Keep them short (3-5 words).

    {{ ctx.output_format }}
  "#
}
