function CheckHealth() -> string {
  client Gemini_31_Flash_Lite_Health
  prompt #"
    {{ _.role("user") }}
    Reply exactly "OK".
  "#
}
