import sys

from app import agent, skills


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "list"}:
        print("usage: python -m app.cli <skill> \"your input\"   (input can also come from stdin)\n")
        for s in skills.list_skills():
            print(f"  {s['name']:<14} {s['description'][:90]}")
        return
    name = sys.argv[1]
    text = " ".join(sys.argv[2:]) or sys.stdin.read()
    print(agent.run_skill(name, text))


if __name__ == "__main__":
    main()
