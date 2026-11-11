# Craft: compressing documentation without losing what matters

Read this before writing the first page. It distills how the best technical teachers compress material: tldr-pages, Go by Example, Learn X in Y Minutes, Diátaxis, Beej's guides, Julia Evans, and Wikipedia's lead and infobox conventions. Each rule says where it comes from so you can judge edge cases.

## 1. The reader and their questions

Write for **one specific reader** (Julia Evans: inconsistent assumptions about the reader confuse everyone). The default reader is a working engineer who knows the surrounding stack but has never used this tool. Change it when the user says who it is for. State what you assume in the lead or a `:::background` block, as Beej does at the top of every guide.

That reader arrives with questions in a fixed order. A page answers them in the same order:

| Question | Page part | Borrowed from | Form |
|---|---|---|---|
| What is it, and why would I use it? | Lead | Wikipedia lead, inverted pyramid | 2-4 sentences, subject in **bold** in the first sentence |
| What are the facts I'll look up? | Infobox | Wikipedia, MyAnimeList, fandom wikis | `:::infobox` with `Label: value` rows |
| How does it work? | How it works | Diátaxis explanation | prose plus one diagram that shows the real mechanism |
| What does it look like in use? | By example | Go by Example, Learn X in Y | `:::example`, prose beside code, with output |
| How do I do the common things? | Recipes | tldr-pages | `:::recipes`, at most 8, most common first |
| What do I look up later? | Reference | Diátaxis reference, Wikipedia tables | tables of fields, flags, files, defaults |
| What will bite me? | Pitfalls | Julia Evans: say plainly what is wrong | table: Symptom, Cause, Fix |
| What did this leave out? | Not covered | Beej's scope statements, Wikipedia "Main article" | list of topics, each with one line and a link |
| Did it stick? | Check yourself | retrieval practice | `:::recall`, 3-8 questions, answers hidden |

These are defaults, not a form to fill. Drop a part the subject doesn't need. Never drop the lead, the model, or the self-check.

### Variants by kind of source

- **Feature or concept** (Claude Code skills, React hooks): the default anatomy.
- **Syntax, format or language** (YAML, Go, SQL): make "By example" one realistic annotated file in the Learn X in Y style, where comments state results (`# evaluates to 83`, `# same as the line above`). Keep prose short.
- **CLI tool**: put Recipes right after the lead; the model section can be short.
- **Library or API**: the smallest complete working program first, then the 20% of the surface people use, in one table, then error handling.
- **Framework conventions** (Next.js App Router): a conventions table (file or name, then what it does), plus a lifecycle diagram (`sequence` or `flow`).
- **Overview or landing page** (mostly links): a map. One `nest` or `flow` diagram of the parts, one paragraph per part, and the pointer pass for depth.

## 2. Find the spine before writing

The spine is the 3-7 ideas that make the rest of the documentation predictable. If the reader holds them, they can guess most details correctly. Find it before drafting:

1. List the candidate facts from the outline and the sections you read.
2. For each, ask: *if the reader forgot this, would they be wrong or slow?* Yes means spine or reference. No means Not covered or nothing.
3. Order the spine so each idea needs only the ones before it.

**Keep**, because readers can't reconstruct these:
- mental models that predict behavior (what loads when, who wins, what persists);
- defaults, precedence orders, scopes and lifecycles;
- exact names the reader must type: files, fields, commands, flags;
- limits and numbers: caps, sizes, timeouts;
- failure modes and their symptoms;
- the reason behind a design decision, when the documentation gives one.

**Cut or move to Not covered**:
- marketing, history, repeated introductions, and overview text that restates the page title;
- exhaustive option lists: keep the options people use, put the rest in a table or link to them;
- platform, enterprise and administrator variants, unless the reader asked for them;
- edge cases that take more than a paragraph and affect few readers.

**Add**, because documentation usually leaves it out:
- the problem the thing solves and what people do without it (one or two sentences, not a history lesson);
- definitions of terms the docs use without explaining, as a short glossary or a `:::background` block;
- how it relates to its neighbors, as a comparison table ("use X when ..., use Y when ...");
- an example that combines features, since docs tend to show each feature alone;
- the order in which to learn things.

## 3. Explaining

These rules are Julia Evans' patterns of confusing explanations, turned around, plus Diátaxis' rule that each kind of writing does one job.

- **Concrete before abstract.** Open a section with the example or the situation, then generalize. Don't open with a definition full of new terms.
- **Why before what.** Every mechanism gets its reason. A weak reason beats none. When the docs give no reason, say what breaks without it.
- **One new idea per paragraph.** Introduce a term before you use it, and define it in plain words the first time.
- **Say the concrete thing.** Replace jargon that implies precision ("securely", "seamlessly", "fully managed") with what actually happens.
- **Realistic examples.** Use the docs' own examples or real use; avoid `foo` and `bar` unless the docs use them. Examples must be complete enough to run.
- **Say when something is wrong.** If you show a mistake, label it as a mistake before showing it. Pitfall rows state the wrong belief and the fix.
- **Analogies stay small.** Use at most one, for one idea, and don't extend it.
- **Back claims.** Cite the source or show an example the reader can run.
- **Keep the modes apart** (Diátaxis). Explanation sections don't contain step lists. Recipes don't explain. Reference tables don't narrate. Tutorial-style examples ignore alternatives and link to them instead.
- **Match the design to the tone.** No playful illustrations, mascots or emoji on serious material.

## 4. Sentences

- Put the point first. Use one idea per sentence and keep most sentences under 25 words.
- Write the docs' exact names in code formatting, spelled exactly as the reader will type them.
- Prefer numbers to adjectives: "truncated at 1,536 characters", not "limited in length".
- Use active voice and the present tense. Address the reader as "you" in instructions.
- Use lists for parallel items, tables when three or more items share two or more attributes, and prose for reasoning (because, so, unless, except).
- Cut filler words such as "simply", "just", "easily", "powerful", "robust", "seamlessly", "it's worth noting", "in this section we will" and "let's".
- Keep the tone neutral and plain. No emoji, exclamation marks, jokes or slang.

## 5. Length

- **Lead**: at most about 120 words (the build warns at 160). It must stand alone: someone who reads only the lead and infobox knows what the thing is and when to use it.
- **Page**: 5-12 minutes is typical. Go longer only when a mechanism needs the space to explain it, never to reach full coverage. When a page passes 20 minutes, split it by the reader's tasks, not by the docs' page boundaries.
- **Ratio**: aim for 10-25% of the source's word count. Above 30% means you are copying. Below 5% for a long source usually means the model is missing.
- **Budget the words.** Spend them on the spine and the pitfalls. Recipes and tables are dense by nature, and the lead is short by rule.

## 6. Diagrams

Draw a diagram only where prose fails: order, interaction, precedence, layout or containment. Never draw one to decorate a list.

| Situation | Kind |
|---|---|
| steps in order, decisions, a loop | `flow` |
| actors exchanging messages over time | `sequence` |
| precedence, layers, override order | `stack` |
| a directory layout or hierarchy | `tree` |
| what contains what | `nest` |

- Show the real mechanism with the docs' names. Node labels are nouns; edge labels are verbs or conditions.
- Use at most 8 nodes, and about 3 diagrams per page.
- Every caption says what to notice: "Figure 2. Personal skills override project skills with the same name", not "Figure 2. Skill locations".
- When the docs have a good diagram, use it as an image with its own caption and credit instead of redrawing it.

## 7. Examples, recipes, exercises

- **Worked examples** (Go by Example): one concept per example; the prose beside each code chunk says what to notice, not what the code says; show output when the example demonstrates behavior; each example builds on the one before.
- **Annotated file** (Learn X in Y): for syntax-heavy subjects, one realistic file in which comments do the teaching and state results.
- **Recipes** (tldr-pages): an imperative description ending in a colon, then one command. Put the most common task first and keep at most 8. Mark the parts the reader replaces with `{{snake_case}}` placeholders, and use a placeholder that can't be pasted blindly for anything destructive. Don't explain general concepts in a recipe.
- **Exercises** (Diátaxis tutorials): under 10 minutes, with exact steps that produce a visible result early. A `Check:` line says what the reader should observe. An optional `Variation:` forces the reader to adapt rather than copy.
- **Self-check**: questions that make the reader produce the model ("What decides whether ...?", "Which wins when ...?"), not trivia. 3-8 per page, with answers hidden.

## 8. Citations and honesty

- Every claim about the subject's behavior that a reader might doubt cites a verbatim quote of at most 30 words, one claim per quote. Prefer quoting the rule over quoting an example.
- Quote from a single passage. Use `...` to skip words; never paraphrase inside quotation marks.
- Background knowledge that isn't from the source goes in `:::background`. It must be standard and stable, such as what YAML front matter is or what a glob matches. Never use it for claims about the documented tool.
- Never present output you did not see. Output blocks come from the docs or from a command you ran.
- Not covered must name the big omissions, so the reader knows what they are skipping.

## 9. Review before reporting

Read each page as the reader would, then answer:

- **Lead test**: from the lead and infobox alone, can the reader say what it is and when to use it?
- **Model test**: after How it works, could the reader have predicted the Pitfalls?
- **Do test**: can the reader complete the most common task from the page alone?
- **Recall test**: do the questions test the spine, not trivia?
- **Confusion checklist**: Does any section start abstract? Is a term used before it is defined? Is any claim unsupported? Is any example unrealistic? Is there a "what" without its "why"? Is a mistake shown without being labeled? Does any analogy outstay its welcome? Do the assumptions about the reader change between sections?
- **Honesty**: Does Not covered name what was left out? Is every claim about the tool cited or shown? Is anything presented as observed that wasn't?
