from typing import Any, Optional, Union, Dict, Callable
import sqlalchemy as sa
from szurubooru import db, errors
from szurubooru.func import util
from szurubooru.search import criteria
from szurubooru.search.typing import SaColumn, SaQuery
from szurubooru.search.configs.base_search_config import Filter


Number = Union[int, float]
WILDCARD = '(--wildcard--)'  # something unlikely to be used by the users


def unescape(text: str, make_wildcards_special: bool = False) -> str:
    output = ''
    i = 0
    while i < len(text):
        if text[i] == '\\':
            try:
                char = text[i+1]
                i += 1
            except IndexError:
                raise errors.SearchError(
                    '끝나지 않은 이스케이프 시퀀스 '
                    '(마지막 백슬래시를 잊었나요?)')
            if char not in '*\\:-.,':
                raise errors.SearchError(
                    '끝나지 않은 이스케이프 시퀀스 '
                    '(백슬래시를 잊었나요?)')
        elif text[i] == '*' and make_wildcards_special:
            char = WILDCARD
        else:
            char = text[i]
        output += char
        i += 1
    return output


def wildcard_transformer(value: str) -> str:
    return (
        unescape(value, make_wildcards_special=True)
        .replace('\\', '\\\\')
        .replace('%', '\\%')
        .replace('_', '\\_')
        .replace(WILDCARD, '%'))


def enum_transformer(available_values: Dict[str, Any], value: str) -> str:
    try:
        return available_values[unescape(value.lower())]
    except KeyError:
        raise errors.SearchError(
            '잘못된 값: %r. 가능한 값: %r.' % (
                value, list(sorted(available_values.keys()))))


def integer_transformer(value: str) -> int:
    return int(unescape(value))


def float_transformer(value: str) -> float:
    for sep in list('/:'):
        if sep in value:
            a, b = value.split(sep, 1)
            return float(unescape(a)) / float(unescape(b))
    return float(unescape(value))


def apply_num_criterion_to_column(
        column: Any,
        criterion: criteria.BaseCriterion,
        transformer: Callable[[str], Number] = integer_transformer) -> SaQuery:
    try:
        if isinstance(criterion, criteria.PlainCriterion):
            expr = column == transformer(criterion.value)
        elif isinstance(criterion, criteria.ArrayCriterion):
            expr = column.in_(transformer(value) for value in criterion.values)
        elif isinstance(criterion, criteria.RangedCriterion):
            assert criterion.min_value or criterion.max_value
            if criterion.min_value and criterion.max_value:
                expr = column.between(
                    transformer(criterion.min_value),
                    transformer(criterion.max_value))
            elif criterion.min_value:
                expr = column >= transformer(criterion.min_value)
            elif criterion.max_value:
                expr = column <= transformer(criterion.max_value)
        else:
            assert False
    except ValueError:
        raise errors.SearchError(
            '기준 값 %r 은(는) 숫자여야 합니다.' % (criterion,))
    return expr


def create_num_filter(
        column: Any,
        transformer: Callable[[str], Number] = integer_transformer) -> SaQuery:
    def wrapper(
            query: SaQuery,
            criterion: Optional[criteria.BaseCriterion],
            negated: bool) -> SaQuery:
        assert criterion
        expr = apply_num_criterion_to_column(column, criterion, transformer)
        if negated:
            expr = ~expr
        return query.filter(expr)
    return wrapper


def apply_str_criterion_to_column(
        column: SaColumn,
        criterion: criteria.BaseCriterion,
        transformer: Callable[[str], str] = wildcard_transformer) -> SaQuery:
    if isinstance(criterion, criteria.PlainCriterion):
        expr = column.ilike(transformer(criterion.value))
    elif isinstance(criterion, criteria.ArrayCriterion):
        expr = sa.sql.false()
        for value in criterion.values:
            expr = expr | column.ilike(transformer(value))
    elif isinstance(criterion, criteria.RangedCriterion):
        raise errors.SearchError(
            '범위가 지정된 기준은 이 컨텍스트에서 유효하지 않습니다. '
            '점들을 이스케이프하는 것을 잊었나요?')
    else:
        assert False
    return expr


def create_str_filter(
        column: SaColumn,
        transformer: Callable[[str], str] = wildcard_transformer) -> Filter:
    def wrapper(
            query: SaQuery,
            criterion: Optional[criteria.BaseCriterion],
            negated: bool) -> SaQuery:
        assert criterion
        expr = apply_str_criterion_to_column(column, criterion, transformer)
        if negated:
            expr = ~expr
        return query.filter(expr)
    return wrapper


def apply_date_criterion_to_column(
        column: SaQuery, criterion: criteria.BaseCriterion) -> SaQuery:
    if isinstance(criterion, criteria.PlainCriterion):
        min_date, max_date = util.parse_time_range(criterion.value)
        expr = column.between(min_date, max_date)
    elif isinstance(criterion, criteria.ArrayCriterion):
        expr = sa.sql.false()
        for value in criterion.values:
            min_date, max_date = util.parse_time_range(value)
            expr = expr | column.between(min_date, max_date)
    elif isinstance(criterion, criteria.RangedCriterion):
        assert criterion.min_value or criterion.max_value
        if criterion.min_value and criterion.max_value:
            min_date = util.parse_time_range(criterion.min_value)[0]
            max_date = util.parse_time_range(criterion.max_value)[1]
            expr = column.between(min_date, max_date)
        elif criterion.min_value:
            min_date = util.parse_time_range(criterion.min_value)[0]
            expr = column >= min_date
        elif criterion.max_value:
            max_date = util.parse_time_range(criterion.max_value)[1]
            expr = column <= max_date
    else:
        assert False
    return expr


def create_date_filter(column: SaColumn) -> Filter:
    def wrapper(
            query: SaQuery,
            criterion: Optional[criteria.BaseCriterion],
            negated: bool) -> SaQuery:
        assert criterion
        expr = apply_date_criterion_to_column(column, criterion)
        if negated:
            expr = ~expr
        return query.filter(expr)
    return wrapper


def create_subquery_filter(
        left_id_column: SaColumn,
        right_id_column: SaColumn,
        filter_column: SaColumn,
        filter_factory: SaColumn,
        subquery_decorator: Callable[[SaQuery], None] = None) -> Filter:
    filter_func = filter_factory(filter_column)

    def wrapper(
            query: SaQuery,
            criterion: Optional[criteria.BaseCriterion],
            negated: bool) -> SaQuery:
        assert criterion
        subquery = db.session.query(right_id_column.label('foreign_id'))
        if subquery_decorator:
            subquery = subquery_decorator(subquery)
        subquery = subquery.options(sa.orm.lazyload('*'))
        subquery = filter_func(subquery, criterion, False)
        subquery = subquery.subquery('t')
        expression = left_id_column.in_(subquery)
        if negated:
            expression = ~expression
        return query.filter(expression)

    return wrapper
