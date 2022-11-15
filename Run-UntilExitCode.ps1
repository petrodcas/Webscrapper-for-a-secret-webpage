param(
    [int[]]$expected_exiting_code = @(0,2),
    [int]$denied_access_exit_code = 3,
    [int]$max_on_denied_access_repeat_tries = 3,
    [string]$params_file='.\run-params.json'
)

if ($max_on_denied_access_repeat_tries -lt 0) {
    $max_on_denied_access_repeat_tries = 0
} 

function Test-IsNotNull {
    param ($p)
    $null -ne $p
}

$params = Get-Content -Raw -Encoding UTF8 -Path $params_file | ConvertFrom-Json
$first_question = if (Test-IsNotNull $params.first_question) { $params.first_question } else {1}
$error_log_path = if (Test-IsNotNull $params.error_log_path) { $params.error_log_path } else {'./error_log.txt'}
$max_skipped_urls = if (Test-IsNotNull $params.max_skipped) { $params.max_skipped } else {-1}
$questions_json_file = if (Test-IsNotNull $params.json_file) { $params.json_file } else {'./questions.json'}
$images_download_directory = if (Test-IsNotNull $params.images_download_directory) {$params.images_download_directory} else {'./questions_images'}


$expected_exiting_code = $expected_exiting_code + $denied_access_exit_code
$current_tries = 0

do {
    python .\find_questions.py --first_question $first_question --last_question $params.last_question `
        --search_params_base $params.search_params_base --url_regex_base $params.url_regex_base `
        --max_skipped $max_skipped_urls --error_log_path $error_log_path --json_file $questions_json_file --images_download_dir $images_download_directory
        
    if ($LASTEXITCODE -eq $denied_access_exit_code) {
        $current_tries++
    }
    else {
        $current_tries = 0
    }
    Write-Host "[SCRIPT] Current on denied access tries: [$current_tries/$max_on_denied_access_repeat_tries]"
} while( $LASTEXITCODE -notin $expected_exiting_code -or $current_tries -lt $max_on_denied_access_repeat_tries )

if  ($current_tries -ge $max_on_denied_access_repeat_tries) {
    Write-Host "Execution stopped due to max tries on denied access error code reached"
}
