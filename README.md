# GGRA-Python

Package for text generation using GGRA  
VSCode Syntax Highlighting Extension Id: `floriangeier.ggra-syntax-highlighting`

## GGRA?

- the here defined format for **generative grammars**
- for extensive documentation see `README_GGRA.md`

## Usage:

### Simple example:

Imagine we want to write a simple grammar to specify the structure for greetings. *GGRA* is used to define the grammar and using *py_ggra* we can do various things with it, including generating a random greeting.

in our *.ggra* file (let's call it *grammar.ggra*):
```
S:
  "Hello," <Person> "!"
  "How are you?"

Person:
  "Alice"
  "Bob"
  <Person> "and" <Person>
```

This can generate some simple sentences, like
`Hello, Alice!` or `Hello, Bob and Alice!` (or other name combinations with *and* in between).

 **Some nomenclature:**  
 - `S` and `Person` are *Nonterminals*
 - the block under the Nonterminal name is its *Nonterminal definition*
 - the lines in the Nonterminal definition are *Patterns*.  
   Every *Nt* definition is made up of one or more patterns.
 - Angle brackets in Patterns will be replaced in the output by an instance of the Nonterminal.

---

To actually generate the sentences, in our Python file we write:  
*main.py*:
```python
from py_ggra import parse_file, resolve_nt

with open("grammar.ggra") as file:
    nonterminals = parse_file(file)

sentence = resolve_nt(nonterminals, nt_name="S", params={})
print(" ".join(sentence))
```

`resolve_nt` will resolve the *Nonterminal* (a grammar structure) that we defined with the name `S` in *grammar.ggra*. This means it follows the grammatical structure to generate an output according to our definitions.

> **Note!**  
> `resolve_nt` returns a list of terminals (text parts), so the output will be something like  
> `["Hello,", "Bob", "and", "Alice", "!"]`  
> We have to format this output ourselves.

---

We can define a list of names in **names.json**, which allows us to clean up *grammar.ggra* :

```
S:
  "Hello," <Person> "!"
  "How are you?"

Person:
  <Name>
  <Person> "and" <Person>

Name -> "names.json"
```

> **Note!**  
> All *JSON* files used this way have to be built a certain way; more on that in the GGRA documentation.

*names.json*:
```json
{
    "order": ["..."],
    "content": [
        "Alice",
        "Bob",
        "Charlie"
    ]
}
```

---

If we now want to let other people do the greeting, another feature comes in handy. Take the sentence *"We greet Bob."*. We have to inflect the verb depending on the person.  
**Nonterminal Parameters** allow to do exactly that:

```
S:
  "Hello," <Person> "!"

  <Person> <Greet> <~Person>
  with:
    "1" | "3" | "4" => Person.form
    Person.form => Greet.form

Name -> "names.json"

Person(form):
  "I"
  if form = "1"

  from:
    <Name>
    "she"
  if form = "3"

  from:
    <Person> "and" <Person>
    "we"
  if form = "4"

Greet(form):
  "greets"
  if form = "3"

  "greet"
  if form = "1" | "4"
```

Now there's quite a lot to unpack:
- **Nonterminal parameters** are defined by the **brackets** behind the Nt name
- `with` modifier block below a pattern can be used to apply parameters to Nt instances.

Other than that we see:
- the `if` modifier below a pattern makes this pattern only be chosen if the condition is fulfilled
- `from` can be used to group multiple patterns. This way, a modifier can target many patterns at the same time.
- bars (`|`) are for optionals, where any of the options may be used
- the tilde (`~`) before a Nt instance means it is to be resolved separately from the other ones. Here we use it to **not** apply the grammatical rule from the `with` block to this instance.
