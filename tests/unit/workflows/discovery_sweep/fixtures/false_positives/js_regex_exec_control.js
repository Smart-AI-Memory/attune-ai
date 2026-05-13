// Control: real eval() call in JS.
// The rule must NOT fire here just because the file is JS.
// eval() in JavaScript is just as dangerous as Python eval().

function dangerousEval(userInput) {
    return eval(userInput);
}
