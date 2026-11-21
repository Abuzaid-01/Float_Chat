"""A conservative statement policy for model-written ocean-data queries."""

from collections.abc import Iterator

import sqlparse
from sqlparse import sql, tokens as T

# Functions available to the SQL model. Keep database administration and
# extension functions outside this list. The executor also uses a read-only
# transaction and a timeout, independently of this policy.
_FUNCTIONS = frozenset("""
    abs acos asin atan atan2 avg cast ceil ceiling coalesce corr cos count date
    date_part date_trunc degrees exp extract floor greatest lag lead least ln log
    lower max min nullif percentile_cont percentile_disc pi power radians
    rank dense_rank row_number regr_slope regr_intercept round sign sin sqrt
    stddev stddev_pop stddev_samp sum tan trunc upper variance var_pop var_samp
""".split())
_PARENTHESIZED_SYNTAX = frozenset("""
    and any as between by case distinct else exists filter from group having in join
    not or order over select then when where within
""".split())
_TYPES = frozenset("""
    bigint boolean date double float4 float8 int int2 int4 int8 integer numeric
    real smallint text timestamp timestamptz varchar
""".split())
_FORBIDDEN = frozenset("""
    INTO UNION INTERSECT EXCEPT OFFSET FETCH TABLESAMPLE LOCK UPDATE DELETE
    INSERT CREATE DROP ALTER TRUNCATE GRANT REVOKE COPY CALL DO COLLATE
""".split())


def _groups(token: sql.TokenList) -> Iterator[sql.TokenList]:
    yield token
    for child in token.tokens:
        if child.is_group:
            yield from _groups(child)


def _is_argo_source(source: sql.Token) -> bool:
    if isinstance(source, sql.Parenthesis):
        first = source.token_next(0)[1]
        return first is not None and first.match(T.Keyword.DML, "SELECT")
    if isinstance(source, sql.Identifier):
        # A derived table with an alias starts with a SELECT in parentheses.
        first = source.token_first()
        if isinstance(first, sql.Parenthesis):
            return _is_argo_source(first)
        if not first or first.ttype not in (T.Name, T.Literal.String.Symbol):
            return False
        return source.get_real_name() == "argo_profiles" and source.get_parent_name() in (None, "public")
    return source.ttype in (T.Name, T.Keyword) and source.value.lower() == "argo_profiles"


def is_read_only_argo_select(query: str) -> bool:
    if not query or len(query) > 16000:
        return False
    try:
        statements = sqlparse.parse(query)
        if len(statements) != 1 or not statements[0].token_first().match(T.Keyword.DML, "SELECT"):
            return False
        statement = statements[0]
        tokens = [token for token in statement.flatten() if not token.is_whitespace]
        if any(token.ttype in T.Comment or token.ttype in T.Error for token in tokens):
            return False
        for i, token in enumerate(tokens):
            if token.ttype in T.Keyword and set(token.normalized.split()) & _FORBIDDEN:
                return False
            if token.ttype in T.Name.Placeholder or (token.value == ";" and i < len(tokens) - 1):
                return False
            if token.value == "::":
                if i + 1 >= len(tokens) or tokens[i + 1].normalized.lower().split(" ")[0] not in _TYPES:
                    return False
                if i + 2 < len(tokens) and tokens[i + 2].value == ".":
                    return False
            if i + 1 < len(tokens) and tokens[i + 1].value == "(":
                if token.ttype in T.Name or token.ttype in T.Keyword or token.ttype == T.Literal.String.Symbol:
                    name = token.normalized.strip('"').lower()
                    if name not in _FUNCTIONS | _PARENTHESIZED_SYNTAX | _TYPES:
                        return False
                    if i and tokens[i - 1].value == ".":
                        return False
        has_argo_source = False
        for group in _groups(statement):
            if isinstance(group, sql.Function) and (group.get_name() or "").lower() == "cast":
                expression = next((token for token in group.tokens if isinstance(token, sql.Parenthesis)), None)
                if expression is None:
                    return False
                parts = [token for token in expression.flatten() if not token.is_whitespace]
                as_index = max((i for i, token in enumerate(parts) if token.match(T.Keyword, "AS")), default=-1)
                if as_index < 0 or parts[as_index + 1].normalized.lower().split(" ")[0] not in _TYPES:
                    return False
                if len(parts) > as_index + 2 and parts[as_index + 2].value == ".":
                    return False
            if not any(token.match(T.Keyword.DML, "SELECT") for token in group.tokens):
                continue
            for i, token in enumerate(group.tokens):
                if token.ttype in T.Keyword and (token.normalized == "FROM" or token.normalized.endswith("JOIN")):
                    _, source = group.token_next(i)
                    if source is None or not _is_argo_source(source):
                        return False
                    has_argo_source = True
        return has_argo_source
    except (sqlparse.exceptions.SQLParseError, RecursionError, AttributeError, IndexError):
        return False


def limit_model_query(query: str, default: int = 1000, maximum: int = 10000) -> str:
    statement = sqlparse.parse(query)[0]
    for index, token in enumerate(statement.tokens):
        if token.match(T.Keyword, "LIMIT"):
            _, value = statement.token_next(index)
            if value is None or value.ttype != T.Literal.Number.Integer:
                raise ValueError("LIMIT must be an integer.")
            limit = int(value.value)
            if limit < 0:
                raise ValueError("LIMIT must be nonnegative.")
            if limit > maximum:
                value.value = str(maximum)
            return str(statement)
    return query.rstrip().rstrip(";") + f" LIMIT {default};"
