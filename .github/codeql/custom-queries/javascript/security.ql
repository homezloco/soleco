/**
 * @name Security Issue Detection
 * @description Detects potential security issues in JavaScript code.
 * @kind path-problem
 */

import javascript

from DataFlow::PathGraph path

select path, "Potential security issue found"
