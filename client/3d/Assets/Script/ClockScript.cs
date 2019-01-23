using System;
using System.Text;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

[Serializable]
public class ClockData
{
    public float now;
}

public class ClockScript : MonoBehaviour {
    public float now = 0.00f;

    private Socket m_Socket;
    private Thread m_RecvThread;
    private TaskManager m_TaskManager;
    private byte[] data = new byte[1024];

    private void Start()
    {
        m_TaskManager = GetComponent<TaskManager>();
        ConnectToServer(m_TaskManager.m_TrafficServerAddress, m_TaskManager.m_TrafficServerPort); ;
    }

    void ConnectToServer(string address, int port)
    {
        try
        {
            m_Socket = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
            m_Socket.Connect(IPAddress.Parse(address), port);
            Debug.Log("Clock连接服务器成功");
            SendMsg("clock");
            m_RecvThread = new Thread(ReceiveMsg);
            m_RecvThread.Start();

        }
        catch (System.Exception ex)
        {
            Debug.Log("Clock连接服务器失败！");
            Debug.Log(ex.Message);
        }
    }

    private void ReceiveMsg()
    {
        while (true)
        {
            if (m_Socket.Connected == false)
            {
                Debug.Log("Clock与服务器断开了连接");
                break;
            }

            Array.Clear(data, 0, data.Length);
            m_Socket.Receive(data);

            string result = Encoding.UTF8.GetString(data, 0, data.Length);
            ClockData clock_data = JsonUtility.FromJson<ClockData>(result);
            now = clock_data.now;
        }
    }

    public void SendMsg(string ms)
    {
        byte[] data = new byte[1024];
        data = Encoding.UTF8.GetBytes(ms);
        m_Socket.Send(data);
    }

    void OnDestroy()
    {
        try
        {
            if (m_Socket != null)
            {
                m_Socket.Shutdown(SocketShutdown.Both);
                m_Socket.Close();  //关闭连接
            }

            if (m_RecvThread != null)
            {
                m_RecvThread.Interrupt();
                m_RecvThread.Abort();
            }

        }
        catch (Exception ex)
        {
            Debug.Log(ex.Message);
        }
    }

    public void OnGUI()
    {
        GUI.Box(new Rect(10, 10, 150f, 60f), "Simulation Clock");
        GUI.Label(new Rect(20, 40, 150f, 30f), "Current time is: " + " " + now.ToString("0.0"));
    }
}
