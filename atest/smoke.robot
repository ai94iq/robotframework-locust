*** Settings ***
Library    LocustLibrary

*** Test Cases ***
Create And Run Load Test
    Create Load Test    http://127.0.0.1:8765
    Set Wait Time    0.1s    0.2s
    Add Get Request    Get Root    /    weight=1
    Run Load Test    users=2    spawn_rate=2    run_time=3s    csv_prefix=atest
    Should Have No Failures
    ${stats}=    Get Aggregated Stats
    Log    ${stats}
    Should Meet Error Rate    100%
