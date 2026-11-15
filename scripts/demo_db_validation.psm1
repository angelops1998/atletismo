function Test-DemoDatabaseVerification {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][int]$ExitCode,
        [AllowNull()][object]$Output,
        [Parameter(Mandatory = $true)][string]$ExpectedDatabase
    )

    if ($ExitCode -ne 0 -or $null -eq $Output) { return $false }
    $text = (@($Output) -join "`n").Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return $false }
    return [string]::Equals($text, $ExpectedDatabase, [System.StringComparison]::Ordinal)
}

Export-ModuleMember -Function Test-DemoDatabaseVerification
