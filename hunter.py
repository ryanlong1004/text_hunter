"""
hunter.py

mutlitool for gathering statistics

Ryan Long <ryanlong1004@gmail.com>
"""

import argparse
import csv
import glob
import itertools
import pathlib
from collections import UserList
import logging
from typing import Any, List

DEFAULT_WRITE = {"delimiter": ",", "quotechar": '"', "quoting": csv.QUOTE_NONNUMERIC}

logger = logging.getLogger(__name__)


class Result:
    """represents a *module command* by path and content"""

    def __init__(self, _path: pathlib.Path, content: str) -> None:
        self.path = _path
        self.content = content

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.path}\n{self.content}/>"


def sanitized(command: str):
    """removes useless characters"""
    return command.replace("\n", "").strip()


class Results(UserList):
    """represents a collection of Command"""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {len(self)}/>"

    @property
    def contents(self):
        """non-unique list of raw commands"""
        return [x.content for x in self]

    @property
    def content_occurence(self):
        """dict of raw commands and their occurence"""
        return {item: self.contents.count(item) for item in self.contents}

    @property
    def content_unique(self):
        """list of unique commands, removing newlines, extra spaces
        and other extraneous characters.
        """
        return list(set([sanitized(x) for x in self.contents]))

    @property
    def paths(self):
        """non unique list of all paths corresponding to all commands"""
        return [x.path for x in self]

    @property
    def paths_unique(self):
        """list of unique file paths found in commands"""
        return list(set(self.paths))

    @property
    def heatmap(self):
        """returns dict of command/# of occurences"""
        return sorted(
            commands.content_occurence.items(), key=lambda x: x[1], reverse=True
        )

    @classmethod
    def find(cls, target: pathlib.Path, extensions: List[str], _commands: List[str]):
        """finds commands in files based on file extensions and content"""
        return find_by_headers(target, extensions, _commands)


def files_by_extension(
    target: pathlib.Path, extensions: List[str]
) -> List[pathlib.Path]:
    """returns a list of files from target filtered by extension"""
    return [
        pathlib.Path(_file).resolve()
        for _file in itertools.chain(
            *[
                glob.glob(f"{target.resolve()}/**/*.{x}", recursive=True)
                for x in extensions
            ],
        )
        if not any([pathlib.Path(_file).is_dir()])
    ]


def find_by_headers(
    target: pathlib.Path, extensions: List[str], phrases: List[str]
) -> Results:
    """searches recursively starting with target, filtering by extensions

    `target` is the root path to search

    `extensions` are one or more file extensions.  They must not include
    leading characters.
    correct `txt` vs `*.txt` incorrect

    `phrases` are one or more header-type phrases to look for.

    When any phrase is found, the lines following will be returned until an
    empty line is found.
    """

    _commands = Results()
    for _file in files_by_extension(target, extensions):
        with open(_file, "r", encoding="utf8") as content:
            found = False
            for _line in content.readlines():
                if any(phrase in _line for phrase in phrases):
                    found = True
                if len(_line) <= 1:
                    found = False
                if found is True and "###" not in _line and _line[0] != "#":
                    _commands.append(Result(pathlib.Path(_file), _line))
    return _commands


def write_csv(fields: List[str], data: List[Any]):
    """write headers and data to csv"""
    with open("output.csv", "w", newline="", encoding="utf8") as _file:
        csvwriter = csv.writer(_file, **DEFAULT_WRITE)
        csvwriter.writerow(fields)
        csvwriter.writerows(data)


def print_divider(length=80):
    """print console divider"""
    print("*" * length)


class ViewCLI:
    """interfaces user via cli"""

    @classmethod
    def get_args(cls):
        """get_args display CLI to user and gets options
        Returns:
            Namespace: object-
        """
        parser = argparse.ArgumentParser(description="""Test searching utility""")
        parser.add_argument(
            "target",
            type=pathlib.Path,
            help="root path to search",
        )
        parser.add_argument(
            "-e",
            "--extensions",
            nargs="+",
            help=("extensions to filter by" "ie txt, sh, bat"),
            required=True,
        )

        parser.add_argument(
            "-p",
            "--phrases",
            nargs="+",
            help=("phrases to search for" "ie txt, sh, bat"),
            required=True,
        )

        parser.add_argument(
            "-l",
            "--log",
            default="info",
            help=("Provide logging level. " "Example --log debug', default='info'"),
        )

        return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        handlers=[logging.FileHandler("archive_results.log"), logging.StreamHandler()],
    )

    args = ViewCLI.get_args()

    search_terms = list(args.phrases)
    logger.info("searching for [%s]", ", ".join(search_terms))

    commands = Results.find(
        pathlib.Path(args.target), list(args.extensions), search_terms
    )

    logger.info("results [%s]", commands)
    print_divider()

    for x in commands.heatmap:
        phrase = x[0].replace("\n", "")
        occ = x[1]
        print(f"{phrase}: {occ} [{round((occ / (len(commands))) * 100)}%]")
    print_divider()
