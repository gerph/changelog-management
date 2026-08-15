#!/usr/bin/env python
"""
Show the groups of the changelog with their expected orderings.

The changelogs for releases can include a 'category' at the start, prefixing the description.
This tool assumes that these categories are expected to be listed in a consistent order,
with some categories always before others. In the case of RISC OS Pyromaniac this means that
the lower level features are always before the higher level features. Keeping the consistent
order means that between releases it is easier to see what areas are changing.

The tool can infer what the order is from the files that already exist. This was useful
during the initial creation of an order to try to work out what the order was which had
been created in a largely ad-hoc manner.

It can also compare the orders in each of the releases to one another to say where they are
not using a consistent order. If category Foo is used before Bar in one file and the other
way around in another file, it can be reported. This can be helpful to ensure that we're
getting things the right way each time. And if we move the categories around, we can see
where we've got them wrong.

We can also include an explicit 'recommended.md' file, which describes the order that the
categories are expected to be given in. This can then ensure that we keep to the
recommended ordering.
"""

import argparse
import os
import re
import sys

import cli


class Ordering(object):

    def __init__(self, name, categories=None):
        self.name = name
        self.categories = list(categories or [])

    def __repr__(self):
        return "<{}(name={}, items={})>".format(self.__class__.__name__, self.name,
                                                '+'.join(self.categories))

    def __contains__(self, category):
        return category in self.categories

    def __iter__(self):
        return iter(self.categories)

    def __len__(self):
        return len(self.categories)

    def __getitem__(self, index):
        return self.categories[index]

    def present(self, category):
        return category in self.categories

    def append(self, category):
        self.categories.append(category)

    def extend(self, categories):
        self.categories.extend(categories)

    def is_before(self, a, b):
        if a not in self.categories:
            return False
        if b not in self.categories:
            return False
        a_position = self.categories.index(a)
        b_position = self.categories.index(b)
        return a_position < b_position

    def is_after(self, a, b):
        if a not in self.categories:
            return False
        if b not in self.categories:
            return False
        a_position = self.categories.index(a)
        b_position = self.categories.index(b)
        return a_position > b_position


class Rule(object):

    def __init__(self, source, category):
        # Category a rule applies to
        self.source = source
        self.category = category
        self.weight = 1

    def __repr__(self):
        return "<{}(source '{}')>".format(self.__class__.__name__, self.source)

    def __eq__(self, other):
        return False

    def valid(self, ordering):
        return self.category in ordering

    def check(self, category, ordering):
        # Override this for the rule to pass
        return False


class RuleBefore(Rule):

    def __init__(self, source, category, other):
        self.other = other
        super(RuleBefore, self).__init__(source, category)

    def __repr__(self):
        return "<{}(source '{}', weight {}, {} must be before {})>".format(self.__class__.__name__, self.source,
                                                                           self.weight, self.category, self.other)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.category == other.category and self.other == other.other

    def valid(self, ordering):
        return self.category in ordering and self.other in ordering

    def check(self, ordering):
        return ordering.is_before(self.category, self.other)


class RuleAfter(Rule):

    def __init__(self, source, category, other):
        self.other = other
        super(RuleAfter, self).__init__(source, category)

    def __repr__(self):
        return "<{}(source '{}', weight {}, {} must be after {})>".format(self.__class__.__name__, self.source,
                                                                          self.weight, self.category, self.other)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.category == other.category and self.other == other.other

    def valid(self, ordering):
        return self.category in ordering and self.other in ordering

    def check(self, ordering):
        return ordering.is_after(self.category, self.other)


class Rules(object):

    def __init__(self):
        self.rules = []

    def __iter__(self):
        return iter(self.rules)

    def append(self, rule):
        if rule not in self.rules:
            self.rules.append(rule)
        else:
            # If it's already in there then we can just increment the weight, when we find it
            matched = False
            for existing_rule in self.rules:
                if rule == existing_rule:
                    #print("Rule %r matches %r" % (rule, existing_rule))
                    existing_rule.source += ',' + rule.source
                    existing_rule.weight += 1
                    matched = True
                    break
            if not matched:
                raise RuntimeError("Rule is in the list, but not found?")


    def failing(self, ordering):
        applicable_rules = [rule for rule in self.rules if rule.valid(ordering)]
        #if len(applicable_rules) == 0:
        #    print("No rules for %r" % (ordering,))
        return [rule for rule in applicable_rules if not rule.check(ordering)]

    def score(self, ordering):
        """
        Score the ordering with a ratio of passing rules.
        """
        applicable_rules = [rule for rule in self.rules if rule.valid(ordering)]
        #if len(applicable_rules) == 0:
        #    print("No rules for %r" % (ordering,))
        passing_rules = [rule for rule in applicable_rules if rule.check(ordering)]

        if not applicable_rules:
            # no applicable rules?
            return 0
        applicable_count = sum([rule.weight for rule in applicable_rules])
        passing_count = sum([rule.weight for rule in passing_rules])
        return float(passing_count) / applicable_count


area_re = re.compile(r'([A-Z][a-zA-Z_0-9]+):')


def orders_from_logs(logs, name_for_log):
    """
    Build an Ordering per (log, group) pair, from the category prefixes used
    on each bullet line.

    @param logs:            Iterable of ChangelogFile objects, already in the
                              order they should be reported in.
    @param name_for_log:     Function taking a ChangelogFile and returning the
                              name to key its orderings by (a version number
                              for released logs, a filename for current ones).

    @return: dict keyed by (name, group), value an Ordering of the categories
             used, in the order they were first seen.
    """
    orders = {}
    for log in logs:
        name = name_for_log(log)
        for group, lines in log.groups.items():
            #print("%s:%s" % (name, group))
            key = (name, group)

            areas = Ordering("%s:%s" % (name, group))
            last_area = None
            for line in lines:
                match = area_re.match(line)
                if match:
                    area = match.group(1)
                    if area != last_area:
                        areas.append(area)
                        last_area = area
            if areas:
                orders[key] = areas

    return orders


def read_released_orders():
    all_logs = cli.released_logs()
    logs = sorted(all_logs, key=lambda log: log.version)
    return orders_from_logs(logs, lambda log: log.version.split(' ', 1)[0])


def read_current_orders():
    """
    Read the group orderings from the in-progress 'current' changelog files.

    Unlike released logs, these files have no '## <version>' heading (they
    are collated into one when a release is made), so there is no version
    number to key on; the filename is used instead.
    """
    all_logs = cli.current_logs()
    logs = sorted(all_logs, key=lambda log: log.filename)
    return orders_from_logs(logs, lambda log: os.path.basename(log.filename))


def determine_categories(orders):
    """
    Determine the categories from the orders given.
    """
    all_categories = set()
    for areas in orders.values():
        all_categories.update(set(areas))
    return all_categories


def read_recommended_order():
    """
    Read the recommended order from the guide file.
    """
    recommended = Ordering("Recommended")
    with open(os.path.join(os.path.dirname(__file__), 'recommended.md')) as fh:
        for line in fh:
            if line.startswith('* '):
                recommended.append(line[2:].strip())

    return recommended


def infer_rules_for_order(rules, order):
    for first_index in range(len(order) - 1):
        first = order[first_index]
        for second_index in range(first_index + 1, len(order)):
            second = order[second_index]
            rules.append(RuleBefore(order.name, first, second))

    # Only add the 'after' rule for the last item; all the others will be implicit
    #for first_index in (len(order)-1,):
    for first_index in range(1, len(order)):
        first = order[first_index]
        for second_index in range(first_index):
            second = order[second_index]
            rules.append(RuleAfter(order.name, first, second))


def report_scores(title, rules, orders):
    # Report on each ordering how well they match the inferred rules
    print(title)
    overall_score = 0
    overall_count = 0
    for key, order in sorted(orders.items()):
        score = rules.score(order)
        if len(order) == 1:
            print("%-20s : %7s" % (order.name, '-'))
        else:
            print("%-20s : %7.3f %%" % (order.name, score * 100))
            if score != 1:
                failed = rules.failing(order)
                for fail in failed:
                    print("%-20s : Rule fails: %r" % ("", fail))
                #print("Rules: %r" % (rules.rules_for_order(order),))

            overall_score += score
            overall_count += 1

    print("---")
    if overall_count == 0:
        # Nothing with more than one category to check; nothing to be inconsistent with.
        print("Overall score:       - %% consistent (nothing to check)")
        return 100
    consistency = overall_score / overall_count * 100
    print("Overall score: %7.3f %% consistent" % (consistency,))
    return consistency


def report_suitable_order(rules, all_categories):
    # Let's try to generate an ordering.
    # Find the category that has the most rules, and work towards those with the least.
    rule_counts = []
    for category in all_categories:
        nrules = len([rule for rule in rules if rule.category == category])
        rule_counts.append((nrules, category))
    ordered_categories = sorted(rule_counts, reverse=True)


    # Now add the items, from the most common to the least, finding the place in the list where
    # they have the best score.
    # This will take quite a while as we repeatedly process the rules - it's an O(n^3) algorithm,
    # where n is the number of categories. (actually worse, as we repeat rules when they have been
    # seen in multiple orderings).
    ordering = Ordering('result')
    for index, pair in enumerate(ordered_categories):
        # Generate a list of orderings with their scores.
        (count, category) = pair
        #print("#%-3i : %r (%i rules)" % (index, category, count))
        best_candidate_score = -1
        best_candidate = None
        # For each possible insertion in the list, we work out the score for that order.
        # We keep the best score, favouring later additions to the ordering.
        for position in range(len(ordering) + 1):
            new_order = ordering.categories[:]
            new_order.insert(position, category)
            candidate = Ordering('result', new_order)
            score = rules.score(candidate)
            #print("      %7.3f => index %-3i: %20s <= %s <= %s" % (score, position,
            #                                                       ordering[position - 1] if position > 0 else 'START',
            #                                                       category,
            #                                                       ordering[position] if position < len(ordering) else 'END'))

            if score >= best_candidate_score:
                best_candidate_score = score
                best_candidate = candidate

        ordering = best_candidate
        #print("=> %3i : %r" % (index, ordering))

        #if index == 40:
        #    break


    print("--------")
    print("Inferred ordering:")
    for category in ordering:
        print("* %s" % (category,))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--use-recommendations',
                        action='store_true',
                        help="Use recommendations as well as inferring from releases")
    parser.add_argument('--check-releases',
                        action='store_true',
                        help="Check the releases for consistency")
    parser.add_argument('--check-current',
                        action='store_true',
                        help="Check the in-progress 'current' changelog files for consistency")

    options = parser.parse_args()

    orders = read_released_orders()
    all_categories = determine_categories(orders)
    if options.use_recommendations:
        recommended = read_recommended_order()
        all_categories.update(set(recommended))
    else:
        recommended = None

    rules = Rules()

    # Work out the rules from the relationships in each ordered item
    for key, order in orders.items():
        infer_rules_for_order(rules, order)

    if recommended:
        infer_rules_for_order(rules, recommended)

    # Only released (and recommended) orderings define the rules: an in-progress
    # 'current' entry may only have one or two categories used so far, and
    # shouldn't be allowed to bend what's considered a consistent order for
    # everything else.
    consistent = True

    if options.check_releases:
        consistency = report_scores("Existing releases, and how consistent they are with the orders used in the rest of the releases", rules, orders)
        if consistency != 100:
            consistent = False

    if options.check_current:
        current_orders = read_current_orders()
        consistency = report_scores("In-progress branch changelogs, and how consistent they are with the released order", rules, current_orders)
        if consistency != 100:
            consistent = False

    if (options.check_releases or options.check_current) and not consistent:
        # Ensure that we exit with a failure if we're not consistent.
        sys.exit(1)

    # If we're using the recommended file, there's no point in offering an alternative order.
    if not options.use_recommendations:
        report_suitable_order(rules, all_categories)


if __name__ == '__main__':
    main()
