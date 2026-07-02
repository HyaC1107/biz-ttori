import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { HistoryListType } from "../../../component/interface/history";
import { histroyAPI } from "../api/histroy";
import { SelectedItem } from "../modal/FilterModal";

export type FilterKey = "materials" | "statuses" | "storages" | "workers";

const join = (items: SelectedItem[]) => items.map((i) => i.id).join(",");

const useHistoryList = () => {
  const [list, setList] = useState<HistoryListType[]>([]);
  const [cnt, setCnt] = useState<number>(0);
  const [perPage, setPerPage] = useState(10);
  const [currentpage, setCurrentpage] = useState(1);
  const [search_key, setSearch_key] = useState("mat_name");
  const [search_value, setSearch_value] = useState("");

  // 컬럼 필터 (다중선택)
  const [materials, setMaterials] = useState<SelectedItem[]>([]); // 자재+규격 (id=mat_seq)
  const [statuses, setStatuses] = useState<SelectedItem[]>([]); // 상태 (id=his_type)
  const [storages, setStorages] = useState<SelectedItem[]>([]); // 위치 (id=sto_seq)
  const [workers, setWorkers] = useState<SelectedItem[]>([]); // 담당자 (id=worker)

  // 기간 필터
  const [startDt, setStartDt] = useState("");
  const [endDt, setEndDt] = useState("");

  const setting_search_key = (e: ChangeEvent<HTMLSelectElement>) =>
    setSearch_key(e.target.value);

  const loadList = useCallback(async () => {
    try {
      const data = await histroyAPI.load({
        current_page: currentpage,
        per_page: perPage,
        ...(search_value && { search_key, search_value }),
        // 컬럼 필터 — 콤마 join 다중값 (백엔드 연동 예정)
        ...(materials.length && { mat_seq: join(materials) }),
        ...(statuses.length && { his_type: join(statuses) }),
        ...(storages.length && { sto_seq: join(storages) }),
        ...(workers.length && { worker: join(workers) }),
        // 기간
        ...(startDt && { start_dt: startDt }),
        ...(endDt && { end_dt: endDt }),
      });
      setList(data.historyList || []);
      setCnt(data.total || 0);
    } catch (err) {
      console.log(err);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    currentpage,
    perPage,
    search_value,
    materials,
    statuses,
    storages,
    workers,
    startDt,
    endDt,
  ]);

  // 페이지당 개수 변경 (페이지 리셋)
  const settingPerPage = (e: ChangeEvent<HTMLSelectElement>) => {
    setCurrentpage(1);
    setPerPage(Number(e.target.value));
  };

  // 기간 변경 (페이지 리셋)
  const settingStart = (e: ChangeEvent<HTMLInputElement>) => {
    setCurrentpage(1);
    setStartDt(e.target.value);
  };
  const settingEnd = (e: ChangeEvent<HTMLInputElement>) => {
    setCurrentpage(1);
    setEndDt(e.target.value);
  };

  useEffect(() => {
    loadList();
  }, [loadList]);

  // 필터 변경 시 1페이지로 (선택값 set + 페이지 리셋)
  const applyFilter = (key: FilterKey, selected: SelectedItem[]) => {
    setCurrentpage(1);
    if (key === "materials") setMaterials(selected);
    if (key === "statuses") setStatuses(selected);
    if (key === "storages") setStorages(selected);
    if (key === "workers") setWorkers(selected);
  };

  // 칩 개별 제거
  const removeChip = (key: FilterKey, id: string | number) => {
    setCurrentpage(1);
    const without = (prev: SelectedItem[]) => prev.filter((i) => i.id !== id);
    if (key === "materials") setMaterials(without);
    if (key === "statuses") setStatuses(without);
    if (key === "storages") setStorages(without);
    if (key === "workers") setWorkers(without);
  };

  // 전체 초기화
  const clearAll = () => {
    setCurrentpage(1);
    setMaterials([]);
    setStatuses([]);
    setStorages([]);
    setWorkers([]);
    setSearch_value("");
    setStartDt("");
    setEndDt("");
  };

  const hasAnyFilter =
    materials.length > 0 ||
    statuses.length > 0 ||
    storages.length > 0 ||
    workers.length > 0 ||
    search_value !== "" ||
    startDt !== "" ||
    endDt !== "";

  return {
    list,
    paging: { cnt, currentpage, setCurrentpage, perPage, setPerPage: settingPerPage },
    search: {
      setting: setSearch_value,
      key: search_key,
      settingKey: setting_search_key,
    },
    filters: {
      materials,
      statuses,
      storages,
      workers,
      applyFilter,
      removeChip,
      clearAll,
      hasAnyFilter,
    },
    period: {
      start: startDt,
      end: endDt,
      setStart: settingStart,
      setEnd: settingEnd,
    },
  };
};

export default useHistoryList;
