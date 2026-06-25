using System;
using System.Diagnostics;
using System.IO;
using System.Text;

class Program
{
    static int Main(string[] args)
    {
        // Lấy tên file thực thi hiện tại (không kèm đuôi) để nhận diện loại shell
        string exeName = Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]).ToLower();
        string shellType = "cmd";
        if (exeName.Contains("powershell"))
        {
            shellType = "powershell";
        }

        // Tìm đường dẫn thư mục bin và thư mục dự án
        string exePath = System.Reflection.Assembly.GetExecutingAssembly().Location;
        string binDir = Path.GetDirectoryName(exePath);
        string projectDir = Path.GetDirectoryName(binDir);
        
        string interceptorPath = Path.Combine(projectDir, "shell_interceptor.py");

        // Chuẩn bị các đối số để gọi Python
        StringBuilder pythonArgs = new StringBuilder();
        pythonArgs.AppendFormat("\"{0}\" --shell {1}", interceptorPath, shellType);

        foreach (string arg in args)
        {
            pythonArgs.Append(" ");
            pythonArgs.Append(EscapeArgument(arg));
        }

        var psi = new ProcessStartInfo();
        psi.FileName = "python";
        psi.Arguments = pythonArgs.ToString();
        psi.UseShellExecute = false;
        psi.RedirectStandardOutput = false;
        psi.RedirectStandardError = false;
        psi.CreateNoWindow = false;

        try
        {
            using (var process = Process.Start(psi))
            {
                process.WaitForExit();
                return process.ExitCode;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("[AgentGuard Wrapper] Error: " + ex.Message);
            return 1;
        }
    }

    // Chuẩn hóa và thoát các ký tự đặc biệt cho đối số dòng lệnh Windows
    private static string EscapeArgument(string arg)
    {
        if (string.IsNullOrEmpty(arg))
        {
            return "\"\"";
        }

        bool needsQuotes = false;
        foreach (char c in arg)
        {
            if (char.IsWhiteSpace(c) || c == '\"' || c == '\\' || c == '|' || c == '&' || c == '>' || c == '<' || c == '^')
            {
                needsQuotes = true;
                break;
            }
        }

        if (!needsQuotes)
        {
            return arg;
        }

        StringBuilder sb = new StringBuilder();
        sb.Append('"');
        for (int i = 0; i < arg.Length; i++)
        {
            char c = arg[i];
            if (c == '\\')
            {
                int backslashes = 0;
                while (i < arg.Length && arg[i] == '\\')
                {
                    backslashes++;
                    i++;
                }

                if (i == arg.Length)
                {
                    sb.Append('\\', backslashes * 2);
                    i--;
                }
                else if (arg[i] == '"')
                {
                    sb.Append('\\', backslashes * 2 + 1);
                    sb.Append('"');
                }
                else
                {
                    sb.Append('\\', backslashes);
                    i--;
                }
            }
            else if (c == '"')
            {
                sb.Append('\\');
                sb.Append('"');
            }
            else
            {
                sb.Append(c);
            }
        }
        sb.Append('"');
        return sb.ToString();
    }
}
