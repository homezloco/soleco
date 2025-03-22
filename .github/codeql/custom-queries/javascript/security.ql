/**
 * @name Security Issue Detection (Dummy Taint Tracking)
 * @description A dummy taint tracking query to demonstrate a custom query configuration.
 * @kind path-problem
 */

import javascript
import semmle.javascript.dataflow.TaintTracking

class DummyConfiguration extends TaintTracking::Configuration {
  DummyConfiguration() { this = "DummyConfiguration" }
  
  // For demonstration purposes, consider every literal to be a source.
  override predicate isSource(DataFlow::Node source) {
    source instanceof Literal
  }
  
  // And every function call to be a sink.
  override predicate isSink(DataFlow::Node sink) {
    sink instanceof CallExpr
  }
}

from DummyConfiguration cfg, TaintTracking::FlowPath path
where cfg.run(cfg, path)
select path, "Dummy taint tracking path"
