import argparse
import json
from .loaders import documents, conversation
from .retrieval import Retriever
from .state import State
from .respond import respond
from .render import render
from .handoff import participants, build_notes


def main():
    parser = argparse.ArgumentParser(description='Offline deterministic billing-support trace')
    parser.add_argument('--conversation', default='data/transcript-dana-whitfield-2026-10-05.txt')
    parser.add_argument('--fixtures', default='data/fixtures.json')
    parser.add_argument('--policy', default='data/policy-bil-pol-014.md')
    parser.add_argument('--kb', default='data/kb-billing-credits.md')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--handoff', action='store_true')
    args = parser.parse_args()
    try:
        rules, articles = documents(args.policy, 'policy'), documents(args.kb, 'kb')
        with open(args.fixtures, encoding='utf-8') as handle:
            fixtures = json.load(handle)
        headers, date, monthly, turns = conversation(args.conversation)
        state, retriever = State(headers, date, monthly, fixtures), Retriever(articles)
        result = dict(conversation=args.conversation, sources={'policy': args.policy, 'kb': args.kb, 'network': 'none'}, rule_titles={key: value['title'] for key, value in rules.items()}, turns=[respond(t, i, state, rules, articles, retriever) for i, t in enumerate(turns, 1)])
        result['participants'] = participants(args.conversation)
        result['handoff_notes'] = build_notes(result, headers, state, result['participants'])
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        render(result, handoff_only=args.handoff)


if __name__ == '__main__':
    main()
