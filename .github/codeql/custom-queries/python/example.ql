/**
 * @name SQL Injection Detection
 * @description Detects potential SQL injection vulnerabilities in Python code
 * @kind path-problem
 * @problem.severity error
 * @precision high
 * @id python/sql-injection
 */

import python
import semmle.python.dataflow.TaintTracking

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
