# paper-toolkit Envelope Schema

Every command prints one JSON envelope with `ok`, `action`, `result`, `state_summary`, `errors`, and `warnings`. Commands with errors exit 1 while still printing the envelope. Use `state_summary` for counts and latest compile state.
