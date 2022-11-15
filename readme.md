# Webscrapper for Secret Webpage

A webscrapper for a certain secret webpage

---

## Getting help

```powershell
    python .\find_questions.py --help
```

---

## Using Run-UntilExitCode.ps1

Modify the *model-params-file.json* to meet the requirements of your *find_questions.py* execution then pass it as a parameter to *Run-UntilExitCode.ps1* so it can loop the execution as needed.

```json
{   
    "json_file": "./questions.json",                 #can be null
    "images_download_directory": "awesome dir name", #can be null
    "first_question": 1,                             #can be null
    "last_question": 1,
    "search_params_base": "some topic question number %d",
    "url_regex_base": "https?://www.secretwebpage.com/view/\\d+-some-topic-question-number-%d/",
    "max_skipped": -1,                               #can be null
    "error_log_path": null                           #can be null
}
```

```powershell
    .\Run-UntilExitCode.ps1 -params_file '.\the-new-json-file.json' -max_on_denied_access_repeat_tries 2
```

By using the previous command, the execution loop will stop only after reaching two consecutive denied access to the website.

