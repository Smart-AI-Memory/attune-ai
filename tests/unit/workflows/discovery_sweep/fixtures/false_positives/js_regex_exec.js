// False-positive fixture: JavaScript regex.exec().
// Scanners that don't language-distinguish flag this as Python exec.
// It is a safe regex method.

const pattern = /([a-z]+)\s+([0-9]+)/;
const match = pattern.exec("hello 42");
if (match) {
    console.log(match[1], match[2]);
}
