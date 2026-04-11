def validate_action(action_name: str) -> bool:
    allowed = {
        "read_house_state",
        "read_power_summary",
        "announce_message",
    }
    return action_name in allowed

if __name__ == "__main__":
    print(validate_action("read_house_state"))
