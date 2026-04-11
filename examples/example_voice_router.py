def resolve_output(room: str) -> str:
    mapping = {
        "deskroom": "desk-speaker",
        "livingroom": "living-speaker",
        "bathroom": "bathroom-speaker",
    }
    return mapping.get(room, "default-speaker")

if __name__ == "__main__":
    print(resolve_output("deskroom"))
