@echo off
:: ROOT = 项目根目录 (此 .bat 在 ops/autostart/, 跳两层)
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

echo ========================================
echo   Aion Chat - ע�Ὺ����������
echo ========================================
echo.

powershell -ExecutionPolicy Bypass -NoProfile -File "%ROOT%\ops\autostart\autostart_install.ps1" -Root "%ROOT%"
if not errorlevel 1 goto :reg_ok

echo.
echo [FAILED] ע��ʧ��,��鿴�Ϸ�����
pause
exit /b 1

:reg_ok
echo.
echo ��� 8080 �˿�...
netstat -ano | findstr "LISTENING" | findstr ":8080" >nul 2>&1
if errorlevel 1 goto :port_free

echo   8080 ���з�������,������ һ������.bat �ֶ�������
echo   �������������Ա���˿ڳ�ͻ,������ע��,�´ε�¼���������Զ��ӹ�
goto :show_summary

:port_free
echo   8080 ����,��������һ��,�������µ�¼...
schtasks /Run /TN "AionChatAutoStart" >nul 2>&1
ping -n 5 127.0.0.1 >nul
netstat -ano | findstr "LISTENING" | findstr ":8080" >nul 2>&1
if errorlevel 1 goto :warn
echo   [OK] ������ͨ����������
goto :show_summary

:warn
echo   [WARN] ������ 8080 ��δ����
echo          �鿴��־: aion-chat\data\logs\autostart.log

:show_summary
echo.
echo ========================================
echo   [OK] ��װ���
echo ========================================
echo   ����: ��ǰ�û���¼ʱ�Զ�����
echo   ��̬: ���غ�̨����,�޴���
echo   ��־: aion-chat\data\logs\autostart.log
echo   ����: 1 ���Ӻ��Զ�����,��� 3 ��
echo   ��֤: ������� http://localhost:8080
echo.
echo   ע��: �㵱ǰ����ͣ������,���¼һ�η���Ż���
echo         ��Ҫ�桤��������,������ Windows �Զ���¼:
echo           1. Win+R ���� netplwiz
echo           2. ȡ����ѡ��Ҫʹ�ñ������,�û����������û��������롹
echo           3. ȷ����������� Windows ��¼����
echo         Win11 ���������ù�ѡ��,���ȸ�ע���:
echo         HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon
echo         �½����޸� DevicePasswordLessBuildVersion=0 ������
echo ========================================
echo.
pause
