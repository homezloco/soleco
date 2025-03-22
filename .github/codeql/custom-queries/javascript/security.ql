/**
 * @name Eval Call Detection
 * @description Detects potential security issues caused by the use of eval in JavaScript.
 * @kind problem
 */

import javascript

from CallExpr call
where call.getTarget().hasName("eval")
select call, "Avoid using eval, as it may lead to security vulnerabilities."
