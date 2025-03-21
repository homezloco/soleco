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

from DataFlow::PathGraph

class SqlInjection extends TaintTracking::Configuration {
  SqlInjection() {
    this = "SQL Injection Vulnerability"
  }

  override predicate isSource(DataFlow::Node source) {
    exists(
      API::Call call |
      call.getTarget().hasQualifiedName("flask", "request", "args") and
      source.asExpr() = call.getArg(0)
    )
  }

  override predicate isSink(DataFlow::Node sink) {
    exists(
      API::Call call |
      call.getTarget().hasQualifiedName("sqlite3", "Cursor", "execute") and
      sink.asExpr() = call.getArg(0)
    )
  }
}
