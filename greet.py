
def greet(name: str) -> str:
    """Return a greeting message for the given name."""
    return f"Hello, {name}!"


def get_greeting_from_user() -> str:
    """Get a greeting by prompting the user for their name."""
    name = input("What is your name? ")
    return greet(name)


if __name__ == "__main__":
    greeting = get_greeting_from_user()
    print(greeting)