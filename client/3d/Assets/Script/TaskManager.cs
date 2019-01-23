using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class InitData
{
    public int[] agv;
    public int[] position;
}

public class TaskManager : MonoBehaviour {

    public GameObject m_LanePrefab;
    public GameObject m_AGVPrefab;
    public GameObject m_TagPrefab;
    public GameObject m_HolderPrefab;
    public string m_SimServerAddress;
    public string m_TrafficServerAddress;
    public int m_TrafficServerPort;
    [HideInInspector]public AGVManager[] m_AGVs;

    private string m_SimId;

	private void Start ()
    {
        GetSimId();
        StartCoroutine(GetInitData());
	}

    private void SpawnMap()
    {
        float xpos = ParameterScript.HSLX;
        float ypos = 0.01f;
        float zpos = ParameterScript.HSLZ;
        for (int i = 0; i <= 5; i++)
        {
            GameObject lanehighspeed = Instantiate(m_LanePrefab, new Vector3(xpos - 4 * i, ypos, zpos), Quaternion.identity) as GameObject;
            LaneScript laneScript = lanehighspeed.GetComponent<LaneScript>();
            laneScript.InitSize(ParameterScript.HSLLength, ParameterScript.onelanewidth, ParameterScript.Direction.Vertical);
        }

        xpos = ParameterScript.CLX;
        zpos = ParameterScript.CLZ;
        for (int i = 0; i <= 40; i++)
        {
            GameObject lanecache = Instantiate(m_LanePrefab, new Vector3(xpos, ypos, zpos + 4 * i), Quaternion.identity) as GameObject;
            LaneScript laneScript = lanecache.GetComponent<LaneScript>();
            laneScript.InitSize(ParameterScript.CLLength, ParameterScript.onelanewidth, ParameterScript.Direction.Horizontal);
        }

        xpos = ParameterScript.LLX;
        zpos = ParameterScript.LLZ;
        for (int i = 0; i <= 5; i++)
        {
            GameObject laneloading = Instantiate(m_LanePrefab, new Vector3(xpos - 4 * i, ypos, zpos), Quaternion.identity) as GameObject;
            LaneScript laneScript = laneloading.GetComponent<LaneScript>();
            laneScript.InitSize(ParameterScript.HSLLength, ParameterScript.onelanewidth, ParameterScript.Direction.Vertical);
        }
    }

    private void SpawnHolders()
    {
        float xpos = 72;
        float ypos = 0;
        float zpos = 2;
        for (int i = 0; i <= 4; i++)
        {
            GameObject holder_yard1 = Instantiate(m_HolderPrefab, new Vector3(xpos, ypos, zpos + 4 * i), Quaternion.identity) as GameObject;
            GameObject holder_yard2 = Instantiate(m_HolderPrefab, new Vector3(xpos, ypos, zpos + 40 + 4 * i), Quaternion.identity) as GameObject;
            GameObject holder_yard3 = Instantiate(m_HolderPrefab, new Vector3(xpos, ypos, zpos + 80 + 4 * i), Quaternion.identity) as GameObject;
            GameObject holder_yard4 = Instantiate(m_HolderPrefab, new Vector3(xpos, ypos, zpos + 120 + 4 * i), Quaternion.identity) as GameObject;
        }
    }

    private void SpawnAGVs(int[] agvs, int[] cells)
    {
        for (int i = 0; i < agvs.Length; i++)
        {
            Vector3 initpos = ParameterScript.Cell2Position(cells[i]);
            Quaternion initrot = Quaternion.Euler(new Vector3(0, -90, 0));
            m_AGVs[i].m_Instance = Instantiate(m_AGVPrefab, initpos, initrot) as GameObject;
            m_AGVs[i].m_Name = "agv_" + agvs[i].ToString();
            m_AGVs[i].m_Address = m_TrafficServerAddress;
            m_AGVs[i].m_Port = m_TrafficServerPort;
            Vector3 tag_position = m_AGVs[i].m_Instance.transform.position + new Vector3(0, 3, 4);
            GameObject tag = Instantiate(m_TagPrefab, tag_position, Quaternion.identity) as GameObject;
            tag.GetComponent<TextMesh>().text = "agv_" + agvs[i].ToString();
            tag.transform.SetParent(m_AGVs[i].m_Instance.transform);
            tag.transform.Rotate(90, 0, 0);
            m_AGVs[i].Setup();
        }
    }

    private void GetSimId()
    {
        string[] CommandLineArgs = Environment.GetCommandLineArgs();
        // m_SimId = CommandLineArgs[1];
        m_SimId = "164";
    }

    private IEnumerator GetInitData()
    {
        string result;
        WWW www = new WWW(m_SimServerAddress + "/get_simdata?sim_id=" + m_SimId);
        yield return www;
        if (www.error != null)
        {
            result = www.error;
            yield return null;
        }
        result = www.text;
        Debug.Log(result);
        InitData init_data = JsonUtility.FromJson<InitData>(result);
        SpawnMap();
        SpawnHolders();
        SpawnAGVs(init_data.agv, init_data.position);
    }
}
