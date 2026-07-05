# d2l command reference

Use global output flags before the command:

```bash
d2l --md grades "calc"
d2l --json dump
```

Core commands:

```bash
d2l --json doctor
d2l setup --list-schools
d2l update
d2l token
d2l whoami
d2l courses
d2l courses --all
d2l --md dump --shallow
d2l --md dump --since 24
d2l --md dump --course "course name"
d2l --md grades "course name"
d2l grades --final
d2l --md assignments "course name"
d2l --md quizzes "course name"
d2l --md due --days 14
d2l --md overdue
d2l --md calendar --days 14
d2l --md news "course name"
d2l --md discussions "course name"
d2l --md content "course name" --toc
d2l --md syllabus "course name"
d2l --md updates
d2l download "course name" "assignment name" -o ./assignment-files
d2l download-content "course name" "module or file name" -o ./course-files
d2l onboard
```

Course args accept fuzzy names, course codes, or numeric org unit IDs. Ask for disambiguation if multiple courses match.
