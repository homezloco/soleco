import python

/**
 * @name Example Query
 * @description Example CodeQL query for Python
 * @kind problem
 * @problem.severity warning
 * @id python/example
 */

from Function f
where f.getName() = "example"
select f, "This is an example function"
