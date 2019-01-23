using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using System.IO;

public class StartSim : MonoBehaviour {

    private string m_SimServerAddress;

    void Start () {
        GameObject task_manager = GameObject.Find("TaskManager");
        m_SimServerAddress = task_manager.GetComponent<TaskManager>().m_SimServerAddress;
        Button btn = this.GetComponent<Button>();
        btn.onClick.AddListener(OnClick);
	}
	
	void OnClick()
    {
        string[] CommandLineArgs = Environment.GetCommandLineArgs();
        // string json_path = CommandLineArgs[2];
        string json_path = "C:\\Users\\lw390\\OneDrive\\EasyTerm\\client\\data\\data\\sim164.json";
        string json_package = File.ReadAllText(json_path);
        Debug.Log(json_package);
        StartCoroutine(RequestStart(json_package));
    }

    private IEnumerator RequestStart(string package)
    {
        string result;
        Dictionary<string, string> headers = new Dictionary<string, string>();
        headers.Add("Content-Type", "application/json");
        byte[] bs = System.Text.UTF8Encoding.UTF8.GetBytes(package);
        WWW www = new WWW(m_SimServerAddress + "/run_sim", bs, headers);
        yield return www;
        if (www.error != null)
        {
            result = www.error;
            yield return null;
        }
        result = www.text;
        Debug.Log(result);

        string[] CommandLineArgs = Environment.GetCommandLineArgs();
        // string data_path = CommandLineArgs[3];
        string data_path = "C:\\Users\\lw390\\OneDrive\\EasyTerm\\client\\data\\sss.json";
        if (!File.Exists(data_path))
        {
            File.WriteAllText(data_path, result);
        }
        else
        {
            File.AppendAllText(data_path, result);
        }
    }
}
