/**
 * @name Security Issue Detection
 * @description Detects potential security issues in JavaScript code.
 * @kind path-problem
 */

import javascript
import semmle.javascript.dataflow.TaintTracking

from TaintTracking::PathGraph path

select path, "Potential security issue found"
