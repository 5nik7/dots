@{
    RootModule = 'AnyPackage.DotNet.ToolProvider.dll'
    ModuleVersion = '0.1.0'
    CompatiblePSEditions = @('Desktop', 'Core')
    GUID = '2f27ec2e-002e-4145-8fd1-8959884ec06b'
    Author = 'Thomas Nieto'
    Copyright = '(c) 2024 Thomas Nieto. All rights reserved.'
    Description = '.Net Tool provider for AnyPackage.'
    PowerShellVersion = '5.1'
    RequiredModules = @(
        @{ ModuleName = 'AnyPackage'; ModuleVersion = '0.5.1' }
    )
    FunctionsToExport = @()
    CmdletsToExport = @()
    AliasesToExport = @()
    PrivateData = @{
        AnyPackage = @{
            Providers = '.NET Tool'
        }
        PSData = @{
            Tags = @('AnyPackage', 'Provider', 'DotNet', 'Tool', 'Windows', 'Linux', "MacOS")
            LicenseUri = 'https://github.com/anypackage/dotnet-tool/blob/main/LICENSE'
            ProjectUri = 'https://github.com/anypackage/dotnet-tool'
        }
    }
    HelpInfoURI = 'https://go.anypackage.dev/help'
}

# SIG # Begin signature block
# MIIlyAYJKoZIhvcNAQcCoIIluTCCJbUCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCB9cVBQiJNRX4+m
# erOCzN8s9lsuUwM4tg9rSUt1JQqLIaCCHzQwggVvMIIEV6ADAgECAhBI/JO0YFWU
# jTanyYqJ1pQWMA0GCSqGSIb3DQEBDAUAMHsxCzAJBgNVBAYTAkdCMRswGQYDVQQI
# DBJHcmVhdGVyIE1hbmNoZXN0ZXIxEDAOBgNVBAcMB1NhbGZvcmQxGjAYBgNVBAoM
# EUNvbW9kbyBDQSBMaW1pdGVkMSEwHwYDVQQDDBhBQUEgQ2VydGlmaWNhdGUgU2Vy
# dmljZXMwHhcNMjEwNTI1MDAwMDAwWhcNMjgxMjMxMjM1OTU5WjBWMQswCQYDVQQG
# EwJHQjEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMS0wKwYDVQQDEyRTZWN0aWdv
# IFB1YmxpYyBDb2RlIFNpZ25pbmcgUm9vdCBSNDYwggIiMA0GCSqGSIb3DQEBAQUA
# A4ICDwAwggIKAoICAQCN55QSIgQkdC7/FiMCkoq2rjaFrEfUI5ErPtx94jGgUW+s
# hJHjUoq14pbe0IdjJImK/+8Skzt9u7aKvb0Ffyeba2XTpQxpsbxJOZrxbW6q5KCD
# J9qaDStQ6Utbs7hkNqR+Sj2pcaths3OzPAsM79szV+W+NDfjlxtd/R8SPYIDdub7
# P2bSlDFp+m2zNKzBenjcklDyZMeqLQSrw2rq4C+np9xu1+j/2iGrQL+57g2extme
# me/G3h+pDHazJyCh1rr9gOcB0u/rgimVcI3/uxXP/tEPNqIuTzKQdEZrRzUTdwUz
# T2MuuC3hv2WnBGsY2HH6zAjybYmZELGt2z4s5KoYsMYHAXVn3m3pY2MeNn9pib6q
# RT5uWl+PoVvLnTCGMOgDs0DGDQ84zWeoU4j6uDBl+m/H5x2xg3RpPqzEaDux5mcz
# mrYI4IAFSEDu9oJkRqj1c7AGlfJsZZ+/VVscnFcax3hGfHCqlBuCF6yH6bbJDoEc
# QNYWFyn8XJwYK+pF9e+91WdPKF4F7pBMeufG9ND8+s0+MkYTIDaKBOq3qgdGnA2T
# OglmmVhcKaO5DKYwODzQRjY1fJy67sPV+Qp2+n4FG0DKkjXp1XrRtX8ArqmQqsV/
# AZwQsRb8zG4Y3G9i/qZQp7h7uJ0VP/4gDHXIIloTlRmQAOka1cKG8eOO7F/05QID
# AQABo4IBEjCCAQ4wHwYDVR0jBBgwFoAUoBEKIz6W8Qfs4q8p74Klf9AwpLQwHQYD
# VR0OBBYEFDLrkpr/NZZILyhAQnAgNpFcF4XmMA4GA1UdDwEB/wQEAwIBhjAPBgNV
# HRMBAf8EBTADAQH/MBMGA1UdJQQMMAoGCCsGAQUFBwMDMBsGA1UdIAQUMBIwBgYE
# VR0gADAIBgZngQwBBAEwQwYDVR0fBDwwOjA4oDagNIYyaHR0cDovL2NybC5jb21v
# ZG9jYS5jb20vQUFBQ2VydGlmaWNhdGVTZXJ2aWNlcy5jcmwwNAYIKwYBBQUHAQEE
# KDAmMCQGCCsGAQUFBzABhhhodHRwOi8vb2NzcC5jb21vZG9jYS5jb20wDQYJKoZI
# hvcNAQEMBQADggEBABK/oe+LdJqYRLhpRrWrJAoMpIpnuDqBv0WKfVIHqI0fTiGF
# OaNrXi0ghr8QuK55O1PNtPvYRL4G2VxjZ9RAFodEhnIq1jIV9RKDwvnhXRFAZ/ZC
# J3LFI+ICOBpMIOLbAffNRk8monxmwFE2tokCVMf8WPtsAO7+mKYulaEMUykfb9gZ
# pk+e96wJ6l2CxouvgKe9gUhShDHaMuwV5KZMPWw5c9QLhTkg4IUaaOGnSDip0TYl
# d8GNGRbFiExmfS9jzpjoad+sPKhdnckcW67Y8y90z7h+9teDnRGWYpquRRPaf9xH
# +9/DUp/mBlXpnYzyOmJRvOwkDynUWICE5EV7WtgwggW2MIIEHqADAgECAhEApPLK
# EVUizMqDeJHsqFBBojANBgkqhkiG9w0BAQwFADBUMQswCQYDVQQGEwJHQjEYMBYG
# A1UEChMPU2VjdGlnbyBMaW1pdGVkMSswKQYDVQQDEyJTZWN0aWdvIFB1YmxpYyBD
# b2RlIFNpZ25pbmcgQ0EgUjM2MB4XDTIyMTIwNjAwMDAwMFoXDTI1MTIwNTIzNTk1
# OVowTDELMAkGA1UEBhMCVVMxDzANBgNVBAgMBkthbnNhczEVMBMGA1UECgwMVGhv
# bWFzIE5pZXRvMRUwEwYDVQQDDAxUaG9tYXMgTmlldG8wggGiMA0GCSqGSIb3DQEB
# AQUAA4IBjwAwggGKAoIBgQDKp+8DxaXlIDZh+gMApqRZ4hD4IDTdRkUEZZqSnUwx
# QnD5k8VpbDeqrEkmww2TKUeOWQbSRMT70T/8R8+ld2GrwzLDQ83k5mrGXIXSXCHR
# iLIZUnLmVjDtf/4FXTEni+acu8dddbCS0GAAzDfnINFgVRQR9GdoaYLqoipRVpLV
# RBzbeR2gSCtzwmpuX1d4NR58NvfUkfzNxy0kaLfqamHl9ae0JHyGvyzrHgOUyt2t
# tA/FidNo8KudwGau/gfyko5egOAURpEqgJHrcaekTVio+GRQs2IFNHIvNnfF9Rm7
# kn5wPZuxWL4UaV5xGyYWLupny3Lpp1n+XlVg6UgYZX25BWwbdbfLvsDPHnlbPB2L
# 0WgCCeG6ZOZjB2dmFaYHhwozRzcvX0FLoYXv1/Vo9QviUTm2QIqb/gaxt3xl/rtc
# CZOjly518iHNR2f1ClS+dPiD7KO5r2owmUsaMZiPVeMnD8/dKT8c9jPhyRBntbX9
# V6hoRXD6J2mf5SKSql8pwC8CAwEAAaOCAYkwggGFMB8GA1UdIwQYMBaAFA8qyyCH
# KLjsb0iuK1SmKaoXpM0MMB0GA1UdDgQWBBQOV7tpbOOE2AnSg3DwNoU56VePWzAO
# BgNVHQ8BAf8EBAMCB4AwDAYDVR0TAQH/BAIwADATBgNVHSUEDDAKBggrBgEFBQcD
# AzBKBgNVHSAEQzBBMDUGDCsGAQQBsjEBAgEDAjAlMCMGCCsGAQUFBwIBFhdodHRw
# czovL3NlY3RpZ28uY29tL0NQUzAIBgZngQwBBAEwSQYDVR0fBEIwQDA+oDygOoY4
# aHR0cDovL2NybC5zZWN0aWdvLmNvbS9TZWN0aWdvUHVibGljQ29kZVNpZ25pbmdD
# QVIzNi5jcmwweQYIKwYBBQUHAQEEbTBrMEQGCCsGAQUFBzAChjhodHRwOi8vY3J0
# LnNlY3RpZ28uY29tL1NlY3RpZ29QdWJsaWNDb2RlU2lnbmluZ0NBUjM2LmNydDAj
# BggrBgEFBQcwAYYXaHR0cDovL29jc3Auc2VjdGlnby5jb20wDQYJKoZIhvcNAQEM
# BQADggGBADWsCefpJbT4oKIh1SXIR4hnfGN/YqI6g3aFIntNgoiurd5uxLkow2WS
# pfaCiXjWjMubDpBvynVvaBsRfcrwT0WGBTwz4miuITPKKkIXYIVb5dCf33ghMJ4U
# D+zHP73ioUtDV545Yeb5WVLrPN8ZCC++u0kX+jck30w56LCvng6gDpPHU/KNroQx
# ENjGpcycTf7Gq9tkcEVbGersD6R64NhI6r8uDH6l0s5NMep1x4yTs0MBPmlB6ZHK
# +88YGDVdfTSYbLpQuvmLkEMHNaPOL0YyTjJJbeaHvGuTfqQb17HDLFJGd70CKrQu
# mvcICrJM9il3B+bNsSKjTLQtGbp5JdJ5paUahybiJKyZlDw5QPRrFEnwHiWaTI/9
# zfRciZyX4kYnLkPpp8rlZFXBqfIzf0gRhgCjVVZoMwZHWqyZNL7gS4C6uvEn2t/3
# BqM7548OuoPLH7W07orz8T7iP7aNYtJpAttZOhAbqB2EKoY3qcKClqKOMQGvc12/
# 16mAKE7E+TCCBhowggQCoAMCAQICEGIdbQxSAZ47kHkVIIkhHAowDQYJKoZIhvcN
# AQEMBQAwVjELMAkGA1UEBhMCR0IxGDAWBgNVBAoTD1NlY3RpZ28gTGltaXRlZDEt
# MCsGA1UEAxMkU2VjdGlnbyBQdWJsaWMgQ29kZSBTaWduaW5nIFJvb3QgUjQ2MB4X
# DTIxMDMyMjAwMDAwMFoXDTM2MDMyMTIzNTk1OVowVDELMAkGA1UEBhMCR0IxGDAW
# BgNVBAoTD1NlY3RpZ28gTGltaXRlZDErMCkGA1UEAxMiU2VjdGlnbyBQdWJsaWMg
# Q29kZSBTaWduaW5nIENBIFIzNjCCAaIwDQYJKoZIhvcNAQEBBQADggGPADCCAYoC
# ggGBAJsrnVP6NT+OYAZDasDP9X/2yFNTGMjO02x+/FgHlRd5ZTMLER4ARkZsQ3hA
# yAKwktlQqFZOGP/I+rLSJJmFeRno+DYDY1UOAWKA4xjMHY4qF2p9YZWhhbeFpPb0
# 9JNqFiTCYy/Rv/zedt4QJuIxeFI61tqb7/foXT1/LW2wHyN79FXSYiTxcv+18Irp
# w+5gcTbXnDOsrSHVJYdPE9s+5iRF2Q/TlnCZGZOcA7n9qudjzeN43OE/TpKF2dGq
# 1mVXn37zK/4oiETkgsyqA5lgAQ0c1f1IkOb6rGnhWqkHcxX+HnfKXjVodTmmV52L
# 2UIFsf0l4iQ0UgKJUc2RGarhOnG3B++OxR53LPys3J9AnL9o6zlviz5pzsgfrQH4
# lrtNUz4Qq/Va5MbBwuahTcWk4UxuY+PynPjgw9nV/35gRAhC3L81B3/bIaBb659+
# Vxn9kT2jUztrkmep/aLb+4xJbKZHyvahAEx2XKHafkeKtjiMqcUf/2BG935A591G
# sllvWwIDAQABo4IBZDCCAWAwHwYDVR0jBBgwFoAUMuuSmv81lkgvKEBCcCA2kVwX
# heYwHQYDVR0OBBYEFA8qyyCHKLjsb0iuK1SmKaoXpM0MMA4GA1UdDwEB/wQEAwIB
# hjASBgNVHRMBAf8ECDAGAQH/AgEAMBMGA1UdJQQMMAoGCCsGAQUFBwMDMBsGA1Ud
# IAQUMBIwBgYEVR0gADAIBgZngQwBBAEwSwYDVR0fBEQwQjBAoD6gPIY6aHR0cDov
# L2NybC5zZWN0aWdvLmNvbS9TZWN0aWdvUHVibGljQ29kZVNpZ25pbmdSb290UjQ2
# LmNybDB7BggrBgEFBQcBAQRvMG0wRgYIKwYBBQUHMAKGOmh0dHA6Ly9jcnQuc2Vj
# dGlnby5jb20vU2VjdGlnb1B1YmxpY0NvZGVTaWduaW5nUm9vdFI0Ni5wN2MwIwYI
# KwYBBQUHMAGGF2h0dHA6Ly9vY3NwLnNlY3RpZ28uY29tMA0GCSqGSIb3DQEBDAUA
# A4ICAQAG/4Lhd2M2bnuhFSCbE/8E/ph1RGHDVpVx0ZE/haHrQECxyNbgcv2FymQ5
# PPmNS6Dah66dtgCjBsULYAor5wxxcgEPRl05pZOzI3IEGwwsepp+8iGsLKaVpL3z
# 5CmgELIqmk/Q5zFgR1TSGmxqoEEhk60FqONzDn7D8p4W89h8sX+V1imaUb693TGq
# Wp3T32IKGfIgy9jkd7GM7YCa2xulWfQ6E1xZtYNEX/ewGnp9ZeHPsNwwviJMBZL4
# xVd40uPWUnOJUoSiugaz0yWLODRtQxs5qU6E58KKmfHwJotl5WZ7nIQuDT0mWjwE
# x7zSM7fs9Tx6N+Q/3+49qTtUvAQsrEAxwmzOTJ6Jp6uWmHCgrHW4dHM3ITpvG5Ip
# y62KyqYovk5O6cC+040Si15KJpuQ9VJnbPvqYqfMB9nEKX/d2rd1Q3DiuDexMKCC
# QdJGpOqUsxLuCOuFOoGbO7Uv3RjUpY39jkkp0a+yls6tN85fJe+Y8voTnbPU1knp
# y24wUFBkfenBa+pRFHwCBB1QtS+vGNRhsceP3kSPNrrfN2sRzFYsNfrFaWz8YOdU
# 254qNZQfd9O/VjxZ2Gjr3xgANHtM3HxfzPYF6/pKK8EE4dj66qKKtm2DTL1KFCg/
# OYJyfrdLJq1q2/HXntgr2GVw+ZWhrWgMTn8v1SjZsLlrgIfZHDCCBuwwggTUoAMC
# AQICEDAPb6zdZph0fKlGNqd4LbkwDQYJKoZIhvcNAQEMBQAwgYgxCzAJBgNVBAYT
# AlVTMRMwEQYDVQQIEwpOZXcgSmVyc2V5MRQwEgYDVQQHEwtKZXJzZXkgQ2l0eTEe
# MBwGA1UEChMVVGhlIFVTRVJUUlVTVCBOZXR3b3JrMS4wLAYDVQQDEyVVU0VSVHJ1
# c3QgUlNBIENlcnRpZmljYXRpb24gQXV0aG9yaXR5MB4XDTE5MDUwMjAwMDAwMFoX
# DTM4MDExODIzNTk1OVowfTELMAkGA1UEBhMCR0IxGzAZBgNVBAgTEkdyZWF0ZXIg
# TWFuY2hlc3RlcjEQMA4GA1UEBxMHU2FsZm9yZDEYMBYGA1UEChMPU2VjdGlnbyBM
# aW1pdGVkMSUwIwYDVQQDExxTZWN0aWdvIFJTQSBUaW1lIFN0YW1waW5nIENBMIIC
# IjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAyBsBr9ksfoiZfQGYPyCQvZyA
# IVSTuc+gPlPvs1rAdtYaBKXOR4O168TMSTTL80VlufmnZBYmCfvVMlJ5LsljwhOb
# toY/AQWSZm8hq9VxEHmH9EYqzcRaydvXXUlNclYP3MnjU5g6Kh78zlhJ07/zObu5
# pCNCrNAVw3+eolzXOPEWsnDTo8Tfs8VyrC4Kd/wNlFK3/B+VcyQ9ASi8Dw1Ps5EB
# jm6dJ3VV0Rc7NCF7lwGUr3+Az9ERCleEyX9W4L1GnIK+lJ2/tCCwYH64TfUNP9vQ
# 6oWMilZx0S2UTMiMPNMUopy9Jv/TUyDHYGmbWApU9AXn/TGs+ciFF8e4KRmkKS9G
# 493bkV+fPzY+DjBnK0a3Na+WvtpMYMyou58NFNQYxDCYdIIhz2JWtSFzEh79qsoI
# WId3pBXrGVX/0DlULSbuRRo6b83XhPDX8CjFT2SDAtT74t7xvAIo9G3aJ4oG0paH
# 3uhrDvBbfel2aZMgHEqXLHcZK5OVmJyXnuuOwXhWxkQl3wYSmgYtnwNe/YOiU2fK
# sfqNoWTJiJJZy6hGwMnypv99V9sSdvqKQSTUG/xypRSi1K1DHKRJi0E5FAMeKfob
# pSKupcNNgtCN2mu32/cYQFdz8HGj+0p9RTbB942C+rnJDVOAffq2OVgy728YUInX
# T50zvRq1naHelUF6p4MCAwEAAaOCAVowggFWMB8GA1UdIwQYMBaAFFN5v1qqK0rP
# VIDh2JvAnfKyA2bLMB0GA1UdDgQWBBQaofhhGSAPw0F3RSiO0TVfBhIEVTAOBgNV
# HQ8BAf8EBAMCAYYwEgYDVR0TAQH/BAgwBgEB/wIBADATBgNVHSUEDDAKBggrBgEF
# BQcDCDARBgNVHSAECjAIMAYGBFUdIAAwUAYDVR0fBEkwRzBFoEOgQYY/aHR0cDov
# L2NybC51c2VydHJ1c3QuY29tL1VTRVJUcnVzdFJTQUNlcnRpZmljYXRpb25BdXRo
# b3JpdHkuY3JsMHYGCCsGAQUFBwEBBGowaDA/BggrBgEFBQcwAoYzaHR0cDovL2Ny
# dC51c2VydHJ1c3QuY29tL1VTRVJUcnVzdFJTQUFkZFRydXN0Q0EuY3J0MCUGCCsG
# AQUFBzABhhlodHRwOi8vb2NzcC51c2VydHJ1c3QuY29tMA0GCSqGSIb3DQEBDAUA
# A4ICAQBtVIGlM10W4bVTgZF13wN6MgstJYQRsrDbKn0qBfW8Oyf0WqC5SVmQKWxh
# y7VQ2+J9+Z8A70DDrdPi5Fb5WEHP8ULlEH3/sHQfj8ZcCfkzXuqgHCZYXPO0EQ/V
# 1cPivNVYeL9IduFEZ22PsEMQD43k+ThivxMBxYWjTMXMslMwlaTW9JZWCLjNXH8B
# lr5yUmo7Qjd8Fng5k5OUm7Hcsm1BbWfNyW+QPX9FcsEbI9bCVYRm5LPFZgb289ZL
# Xq2jK0KKIZL+qG9aJXBigXNjXqC72NzXStM9r4MGOBIdJIct5PwC1j53BLwENrXn
# d8ucLo0jGLmjwkcd8F3WoXNXBWiap8k3ZR2+6rzYQoNDBaWLpgn/0aGUpk6qPQn1
# BWy30mRa2Coiwkud8TleTN5IPZs0lpoJX47997FSkc4/ifYcobWpdR9xv1tDXWU9
# UIFuq/DQ0/yysx+2mZYm9Dx5i1xkzM3uJ5rloMAMcofBbk1a0x7q8ETmMm8c6xdO
# lMN4ZSA7D0GqH+mhQZ3+sbigZSo04N6o+TzmwTC7wKBjLPxcFgCo0MR/6hGdHgbG
# pm0yXbQ4CStJB6r97DDa8acvz7f9+tCjhNknnvsBZne5VhDhIG7GrrH5trrINV0z
# do7xfCAMKneutaIChrop7rRaALGMq+P5CslUXdS5anSevUiumDCCBvUwggTdoAMC
# AQICEDlMJeF8oG0nqGXiO9kdItQwDQYJKoZIhvcNAQEMBQAwfTELMAkGA1UEBhMC
# R0IxGzAZBgNVBAgTEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4GA1UEBxMHU2FsZm9y
# ZDEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMSUwIwYDVQQDExxTZWN0aWdvIFJT
# QSBUaW1lIFN0YW1waW5nIENBMB4XDTIzMDUwMzAwMDAwMFoXDTM0MDgwMjIzNTk1
# OVowajELMAkGA1UEBhMCR0IxEzARBgNVBAgTCk1hbmNoZXN0ZXIxGDAWBgNVBAoT
# D1NlY3RpZ28gTGltaXRlZDEsMCoGA1UEAwwjU2VjdGlnbyBSU0EgVGltZSBTdGFt
# cGluZyBTaWduZXIgIzQwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCk
# kyhSS88nh3akKRyZOMDnDtTRHOxoywFk5IrNd7BxZYK8n/yLu7uVmPslEY5aiAlm
# ERRYsroiW+b2MvFdLcB6og7g4FZk7aHlgSByIGRBbMfDCPrzfV3vIZrCftcsw7oR
# mB780yAIQrNfv3+IWDKrMLPYjHqWShkTXKz856vpHBYusLA4lUrPhVCrZwMlobs4
# 6Q9vqVqakSgTNbkf8z3hJMhrsZnoDe+7TeU9jFQDkdD8Lc9VMzh6CRwH0SLgY4an
# vv3Sg3MSFJuaTAlGvTS84UtQe3LgW/0Zux88ahl7brstRCq+PEzMrIoEk8ZXhqBz
# NiuBl/obm36Ih9hSeYn+bnc317tQn/oYJU8T8l58qbEgWimro0KHd+D0TAJI3Vil
# U6ajoO0ZlmUVKcXtMzAl5paDgZr2YGaQWAeAzUJ1rPu0kdDF3QFAaraoEO72jXq3
# nnWv06VLGKEMn1ewXiVHkXTNdRLRnG/kXg2b7HUm7v7T9ZIvUoXo2kRRKqLMAMqH
# ZkOjGwDvorWWnWKtJwvyG0rJw5RCN4gghKiHrsO6I3J7+FTv+GsnsIX1p0OF2Cs5
# dNtadwLRpPr1zZw9zB+uUdB7bNgdLRFCU3F0wuU1qi1SEtklz/DT0JFDEtcyfZhs
# 43dByP8fJFTvbq3GPlV78VyHOmTxYEsFT++5L+wJEwIDAQABo4IBgjCCAX4wHwYD
# VR0jBBgwFoAUGqH4YRkgD8NBd0UojtE1XwYSBFUwHQYDVR0OBBYEFAMPMciRKpO9
# Y/PRXU2kNA/SlQEYMA4GA1UdDwEB/wQEAwIGwDAMBgNVHRMBAf8EAjAAMBYGA1Ud
# JQEB/wQMMAoGCCsGAQUFBwMIMEoGA1UdIARDMEEwNQYMKwYBBAGyMQECAQMIMCUw
# IwYIKwYBBQUHAgEWF2h0dHBzOi8vc2VjdGlnby5jb20vQ1BTMAgGBmeBDAEEAjBE
# BgNVHR8EPTA7MDmgN6A1hjNodHRwOi8vY3JsLnNlY3RpZ28uY29tL1NlY3RpZ29S
# U0FUaW1lU3RhbXBpbmdDQS5jcmwwdAYIKwYBBQUHAQEEaDBmMD8GCCsGAQUFBzAC
# hjNodHRwOi8vY3J0LnNlY3RpZ28uY29tL1NlY3RpZ29SU0FUaW1lU3RhbXBpbmdD
# QS5jcnQwIwYIKwYBBQUHMAGGF2h0dHA6Ly9vY3NwLnNlY3RpZ28uY29tMA0GCSqG
# SIb3DQEBDAUAA4ICAQBMm2VY+uB5z+8VwzJt3jOR63dY4uu9y0o8dd5+lG3DIscE
# ld9laWETDPYMnvWJIF7Bh8cDJMrHpfAm3/j4MWUN4OttUVemjIRSCEYcKsLe8tqK
# RfO+9/YuxH7t+O1ov3pWSOlh5Zo5d7y+upFkiHX/XYUWNCfSKcv/7S3a/76TDOxt
# og3Mw/FuvSGRGiMAUq2X1GJ4KoR5qNc9rCGPcMMkeTqX8Q2jo1tT2KsAulj7NYBP
# XyhxbBlewoNykK7gxtjymfvqtJJlfAd8NUQdrVgYa2L73mzECqls0yFGcNwvjXVM
# I8JB0HqWO8NL3c2SJnR2XDegmiSeTl9O048P5RNPWURlS0Nkz0j4Z2e5Tb/MDbE6
# MNChPUitemXk7N/gAfCzKko5rMGk+al9NdAyQKCxGSoYIbLIfQVxGksnNqrgmByD
# defHfkuEQ81D+5CXdioSrEDBcFuZCkD6gG2UYXvIbrnIZ2ckXFCNASDeB/cB1Pgu
# Ec2dg+X4yiUcRD0n5bCGRyoLG4R2fXtoT4239xO07aAt7nMP2RC6nZksfNd1H48Q
# xJTmfiTllUqIjCfWhWYd+a5kdpHoSP7IVQrtKcMf3jimwBT7Mj34qYNiNsjDvgCH
# HKv6SkIciQPc9Vx8cNldeE7un14g5glqfCsIo0j1FfwET9/NIRx65fWOGtS5QDGC
# BeowggXmAgEBMGkwVDELMAkGA1UEBhMCR0IxGDAWBgNVBAoTD1NlY3RpZ28gTGlt
# aXRlZDErMCkGA1UEAxMiU2VjdGlnbyBQdWJsaWMgQ29kZSBTaWduaW5nIENBIFIz
# NgIRAKTyyhFVIszKg3iR7KhQQaIwDQYJYIZIAWUDBAIBBQCggYQwGAYKKwYBBAGC
# NwIBDDEKMAigAoAAoQKAADAZBgkqhkiG9w0BCQMxDAYKKwYBBAGCNwIBBDAcBgor
# BgEEAYI3AgELMQ4wDAYKKwYBBAGCNwIBFTAvBgkqhkiG9w0BCQQxIgQgB0jk5DL+
# i9jZVCZHpDfUl4MM2+br8SFNBspgsGIg9sEwDQYJKoZIhvcNAQEBBQAEggGAVri9
# Phu3NynLg77h6oMlYDInJ+EFHAILOZzhbREJz8ygg7uSE0YMbkuRYj++BeOP4IuJ
# ceNKG8lz/oqGe5TNojvTMfwb0kBdaqsDAMWToGZMIJ2Z0V1Ze7yMGcv556FQRv4T
# BYj4eTs4hlLpyEr2oOOQldD6br7EZi+i1c5gPcEYH+sNW2mDXr3XTKfuuIpQtYX1
# AkxxrjpIlxM7tb/VhB68gATUBBn9HGqb9HAmwwwKDB0MToBiF0ng6Kv0RuTUmroz
# wzhIa4//8nPwza2NznOe1iBSD9hTEgAkGgiR+ufqKoqlMHt/I8UQBx28K0LyMMgy
# VbGP168N62mAhF1pV5vb9qD1ZjCjwbPrC9CpjYkztxLneu07Fmti+9wYNhST5tTc
# yraef83HNse+29KAtnZPhIA23FW5AFR0DPTAga3Gbvk3dss0zN9qsjfxQyGQrau2
# tdgP8rtzOVRbY3UjoNDu3RYxkpFbXa4el7Pghri/nLmYBhE4wLQMFa+FEA01oYID
# SzCCA0cGCSqGSIb3DQEJBjGCAzgwggM0AgEBMIGRMH0xCzAJBgNVBAYTAkdCMRsw
# GQYDVQQIExJHcmVhdGVyIE1hbmNoZXN0ZXIxEDAOBgNVBAcTB1NhbGZvcmQxGDAW
# BgNVBAoTD1NlY3RpZ28gTGltaXRlZDElMCMGA1UEAxMcU2VjdGlnbyBSU0EgVGlt
# ZSBTdGFtcGluZyBDQQIQOUwl4XygbSeoZeI72R0i1DANBglghkgBZQMEAgIFAKB5
# MBgGCSqGSIb3DQEJAzELBgkqhkiG9w0BBwEwHAYJKoZIhvcNAQkFMQ8XDTI0MDMy
# NTAyNTkwMVowPwYJKoZIhvcNAQkEMTIEMKNTgorKlVvWHgmgTiZqWyqzWk7AE65I
# mUc5gIqPvgM2YyOI0rWeKSDeeemtqDPPUDANBgkqhkiG9w0BAQEFAASCAgB9bOWw
# +1ne6mKtu9pimciD0rXpeWn8sADwtPezQU5NTOHbkyAYy8bJgqrPXHmSadBYI7qE
# 0jPD4RY2DZT4uSHcNtTG+C8S4SKqwDNDIrwmN/UsMGuUdornTOx4tbAPkV6cpEkw
# Ov4lnjDWpQJrPPLKSXxVSGjWYDRXbO2BdT+mbAUz3uf5YlvCqg4Np0iTCpeB6IEO
# B8EiLyo1hEhGaRTsneJi7pyedrYGGL1teTQncbjOILCgdcDgtEuJaBhLV9PQXP4Z
# Z+KrEvSAV4rlqCHOTKMWlRrhr0SnjAe7qwrgCmx4uovPufZvYqrORMgP07mXPj1o
# 3lR3so3aV8/Rz6MBnBOU31LZ28HeDQLUxfLoYJTNFOcrCfLdEfAzrDi/y4baieb0
# uP0YK1t0B0BEAqmi1swYtPsEq10H6rtG8tNZ3nupGF82Cjty4twWp9AFSU6EzWPu
# JUS5NE8xeCDscHzdl42u6FIXi/VENGXyLZtbY/OO9z/JkA8QCt4IYz735R/MNZ/r
# olUBc/eGQfzfsX9AagSxWh1B3ZrJ+hnOe/VSc7P9n1bkwi68fRVrIJmJSBJOGhIv
# sxQq0Y3S2IbPAsRBURplCf/dbSVlniNhbQTLB1JwRQ3nkjOzgJHXV2emjB+Ti+Dd
# xxRZ8zYjzCnrfhFoZHsb2uELN3pixPKAg6lwKg==
# SIG # End signature block