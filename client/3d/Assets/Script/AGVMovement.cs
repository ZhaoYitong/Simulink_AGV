using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class AGVMovement : MonoBehaviour {

    [HideInInspector] public AGVManager m_Manager;
    [HideInInspector] public int flag;
    public GameObject m_ContainerPrefeb;

    private List<Hashtable> commands = new List<Hashtable>();
    private GameObject m_Container;

    public void AddPath(int[] paths, float speed)
    {
        Vector3[] new_paths = new Vector3[paths.Length];
        for (int i = 0; i < paths.Length; i++)
        {
            new_paths[i] = ParameterScript.Cell2Position(paths[i]);
        }
        Hashtable command = new Hashtable();
        command.Add("path", new_paths);
        command.Add("easeType", iTween.EaseType.easeInOutSine);
        command.Add("speed", speed);
        command.Add("movetopath", false);
        command.Add("orienttopath", true);
        command.Add("oncomplete", "OnPathComplete");
        command.Add("oncompleteparams", paths[paths.Length - 1]);
        commands.Add(command);
        Debug.Log("Add path to " + m_Manager.m_Name + command.ToString());
    }

    private void OnPathComplete(int cell)
    {
        m_Manager.SendMsg(cell.ToString());
    }

    private void Start ()
    {
        Vector3 container_position = transform.position + new Vector3(0, 1.3f, 0);
        m_Container = Instantiate(m_ContainerPrefeb, container_position, transform.rotation) as GameObject;
        m_Container.GetComponent<Transform>().SetParent(GetComponent<Transform>());
        StartCoroutine(Move());
    }

	private void Update ()
    {
		if (flag == 1)
        {
            m_Container.GetComponent<Renderer>().enabled = true;
        }
        else
        {
            m_Container.GetComponent<Renderer>().enabled = false;
        }
    }

    private IEnumerator Move()
    {
        while (true)
        {
            if (commands.Count != 0)
            {
                Hashtable command = commands[0];
                iTween.MoveTo(gameObject, command);
                commands.RemoveAt(0);
            }
            else
            {
                yield return new WaitForSeconds(0.1f);
            }
        }
    }
}
