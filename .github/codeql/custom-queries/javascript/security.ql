/**
 * @name Eval Call Detection
 * @id js/eval-call-detection
 * @description Detects potential security issues caused by the use of eval in JavaScript.
 * @kind problem
 */

import javascript

from CallExpr call, Identifier id
where call.getCallee() = id and id.getName() = "eval"
select call, "Avoid using eval, as it may lead to security vulnerabilities."
